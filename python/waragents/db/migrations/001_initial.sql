-- The WarAgents schema.
--
-- Accounts, ownership, games and their outcomes are normalised into tables with foreign keys.
-- Values that are always read and written whole stay as jsonb: a map's grids, a tree's nodes,
-- and the copies of the map and trees a game was played with, which replay it and must never
-- change. Ids are the readable slugs the app already uses ("skirmish", "graze", "alice").

create domain slug as text check (value ~ '^[a-z0-9][a-z0-9-]{0,79}$');

-- ---- accounts ---------------------------------------------------------------------------

create table players (
    id          slug primary key,                 -- the username
    name        text not null check (btrim(name) <> ''),
    colour      text check (colour ~ '^#[0-9a-fA-F]{6}$'),
    -- The default tree, by name: looked up in their own trees and then the default trees,
    -- like CHANGE_TREE, so it isn't a foreign key.
    start_tree  text,
    xp          integer not null default 0 check (xp >= 0),
    is_admin    boolean not null default false,
    created_at  timestamptz not null default now()
);

-- Kept apart from players so profiles can be shared (with an analytics role, say) without
-- the password hashes.
create table credentials (
    player_id     slug primary key references players on delete cascade,
    password_hash text not null,
    updated_at    timestamptz not null default now()
);

-- Server-wide values, such as the key that signs session cookies.
create table settings (
    key   text primary key,
    value text not null
);

-- ---- maps and trees ---------------------------------------------------------------------

create table maps (
    id          slug primary key,
    name        text not null check (btrim(name) <> ''),
    owner_id    slug references players on delete restrict,  -- null for a system map
    published   boolean not null default false,
    mode        text not null check (mode in ('CLICK', 'CONST', 'FIXED')),
    max_agents  integer not null check (max_agents >= 1),
    width       integer not null check (width >= 1),
    height      integer not null check (height >= 1),
    -- {"dirt": [[...]], "food": [[...]], "plants": [...], "starts": [...]}, row n is y = n
    layout      jsonb not null,
    criteria    jsonb not null default '[]',
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);
create index maps_owner on maps (owner_id);

create table trees (
    id          slug primary key,
    name        text not null check (btrim(name) <> ''),
    owner_id    slug references players on delete restrict,  -- null for a default tree
    root        jsonb,                                       -- null while it's empty
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now(),
    constraint trees_owner_name unique nulls not distinct (owner_id, name)
);

-- ---- training ---------------------------------------------------------------------------

create table tutorials (
    id          slug primary key,
    name        text not null,
    track       text not null,
    position    integer not null,              -- its "order" within the track
    level       text not null,
    max_turns   integer not null check (max_turns >= 1),
    content     jsonb not null                 -- brief, goal, hints, map, team, bots, solution, ...
);

create table tutorial_progress (
    player_id     slug references players on delete cascade,
    tutorial_id   slug references tutorials on delete cascade,
    completed_at  timestamptz not null default now(),
    best_turns    integer not null check (best_turns >= 0),
    primary key (player_id, tutorial_id)
);

-- ---- seasons ----------------------------------------------------------------------------

create table seasons (
    id          slug primary key,
    name        text not null check (btrim(name) <> ''),
    status      text not null check (status in ('open', 'closed')),
    started_at  timestamptz not null default now(),
    ended_at    timestamptz
);
create unique index seasons_one_open on seasons (status) where status = 'open';

create table season_ratings (
    season_id   slug references seasons on delete cascade,
    player_id   slug references players on delete cascade,
    rating      double precision not null,
    games       integer not null default 0,
    wins        integer not null default 0,
    primary key (season_id, player_id)
);

-- The final standings, written when a season ends.
create table season_standings (
    season_id   slug references seasons on delete cascade,
    player_id   slug references players on delete cascade,
    band        integer not null,
    rank        integer not null,       -- place on the whole leaderboard
    band_rank   integer,                -- place within the band; null if too few games to rank
    level       integer not null,
    rating      double precision not null,
    games       integer not null,
    wins        integer not null,
    reward      integer not null default 0,
    xp_before   integer,                -- null for an unranked player, who gets no reward
    primary key (season_id, player_id)
);

-- ---- games ------------------------------------------------------------------------------

create table games (
    id          text primary key,
    name        text not null,
    mode        text not null check (mode in ('sandbox', 'training', 'skirmish', 'season')),
    seed        bigint not null,
    rules       integer,
    max_turns   integer,
    created_at  timestamptz not null default now(),
    created_by  slug references players on delete set null,
    map_id      slug references maps on delete set null,       -- null for a generated map
    season_id   slug references seasons on delete set null,
    tutorial_id slug references tutorials on delete set null,
    map         jsonb not null,           -- the map as it was when the game started
    criteria    jsonb not null,           -- the win conditions for the teams that played
    extra       jsonb not null default '{}'
);
create index games_created_by on games (created_by, created_at desc);
create index games_map on games (map_id);
create index games_season on games (season_id);
create index games_tutorial on games (tutorial_id);

create table game_teams (
    game_id      text references games on delete cascade,
    slot         integer not null,
    position     integer not null,        -- the order the teams were listed in
    name         text not null,
    colour       text,
    player_id    slug references players on delete set null,
    speed        integer not null,
    health       integer not null,
    power        integer not null,
    start_health integer,
    start_tree   text not null,
    -- The catalogue tree the team started with, when it came from one, so a tree's games can be
    -- found later. trees holds the copies that were played.
    tree_id      slug references trees on delete set null,
    trees        jsonb not null,
    primary key (game_id, slot)
);
create index game_teams_player on game_teams (player_id);
create index game_teams_tree on game_teams (tree_id);

-- ---- results ----------------------------------------------------------------------------

create table results (
    game_id     text primary key references games on delete cascade,
    reason      text not null,
    outcome     text not null,
    turns       integer not null,
    winners     integer[] not null,
    finished_at timestamptz not null default now()
);

create table placements (
    game_id     text references results on delete cascade,
    slot        integer not null,
    position    integer not null,
    place       integer not null,
    alive       integer not null,
    agents      integer not null,
    exp         integer not null,
    eliminated  integer,                  -- the turn the team was knocked out
    primary key (game_id, slot),
    foreign key (game_id, slot) references game_teams (game_id, slot) on delete cascade
);

-- The account XP (and Season rating) each player got from a game.
create table rewards (
    game_id       text references results on delete cascade,
    player_id     slug references players on delete cascade,
    agent_xp      integer not null,
    from_agents   integer not null,
    bonus         integer not null,
    total         integer not null,
    xp_before     integer not null,
    xp_after      integer not null,
    rating_before double precision,
    rating_after  double precision,
    primary key (game_id, player_id)
);
create index rewards_player on rewards (player_id);

create table result_views (
    game_id     text references results on delete cascade,
    player_id   slug references players on delete cascade,
    seen_at     timestamptz not null default now(),
    primary key (game_id, player_id)
);
