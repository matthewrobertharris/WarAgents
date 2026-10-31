-- Friends. A player asks another to be friends, and they're friends once the other accepts. Until
-- then only the two of them see the request. Either can withdraw or end it at any time.

create table friendships (
    requester_id  slug not null references players on delete cascade,
    addressee_id  slug not null references players on delete cascade,
    status        text not null check (status in ('pending', 'accepted')),
    requested_at  timestamptz not null default now(),
    accepted_at   timestamptz,
    primary key (requester_id, addressee_id),
    check (requester_id <> addressee_id),
    check ((status = 'accepted') = (accepted_at is not null))
);

-- One friendship per pair of players, whichever of them asked.
create unique index friendships_pair on friendships (least(requester_id, addressee_id), greatest(requester_id, addressee_id));
create index friendships_addressee on friendships (addressee_id);
