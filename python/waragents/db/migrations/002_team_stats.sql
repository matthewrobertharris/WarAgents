-- What each team did in a finished game, for the Analytics screen (stats.py counts it).

-- Which version of its trees a team played: a fingerprint of the copies it played with, so games
-- of the same tree before and after an edit can be told apart. jsonb's text form is canonical,
-- so the same trees always give the same fingerprint.
alter table game_teams add column tree_hash text generated always as (md5(trees::text)) stored;
create index game_teams_tree_version on game_teams (tree_id, tree_hash);

create table team_stats (
    game_id        text,
    slot           integer,
    stats_version  integer not null,
    kills          integer not null,
    deaths         integer not null,
    births         integer not null,
    damage_dealt   integer not null,
    damage_taken   integer not null,
    blocks         integer not null,
    food_eaten     integer not null,
    confused       integer not null,
    peak_agents    integer not null,
    agents         integer[] not null,   -- agents alive at the end of each turn, from turn 0
    health         integer[] not null,   -- their total health at the end of each turn
    primary key (game_id, slot),
    foreign key (game_id, slot) references game_teams (game_id, slot) on delete cascade
);

-- How often a team chose each action, and whether it worked.
create table team_actions (
    game_id    text,
    slot       integer,
    action     text not null,
    succeeded  integer not null,
    failed     integer not null,
    primary key (game_id, slot, action),
    foreign key (game_id, slot) references team_stats (game_id, slot) on delete cascade
);

-- How often each node of a team's trees was visited, and how often it confused an agent. node_id
-- is the node's place in the tree in pre-order, in the copy of the tree the team played.
create table team_node_visits (
    game_id    text,
    slot       integer,
    tree_name  text not null,
    node_id    integer not null,
    visits     integer not null,
    confused   integer not null default 0,
    primary key (game_id, slot, tree_name, node_id),
    foreign key (game_id, slot) references team_stats (game_id, slot) on delete cascade
);
