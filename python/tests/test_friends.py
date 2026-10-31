"""Friends: asking, accepting, declining and removing, who sees what, and public profiles."""

import pytest
from conftest import sign_up


@pytest.fixture
def people(app):
    admin = sign_up(app, "Admin")
    return {"admin": admin, "alice": sign_up(app, "Alice"), "bob": sign_up(app, "Bob"), "carol": sign_up(app, "Carol")}


def names(client):
    lists = client.get("/api/friends").json
    return {kind: [p["id"] for p in players] for kind, players in lists.items()}


def test_a_request_becomes_a_friendship_once_accepted(people):
    alice, bob = people["alice"], people["bob"]
    sent = alice.post("/api/friends", json={"name": "Bob"})
    assert sent.status_code == 201 and sent.json == {"player": "bob", "friendship": "sent"}
    # Neither is in the other's friends yet: Alice is waiting, and Bob has a request to answer.
    assert names(alice) == {"friends": [], "received": [], "sent": ["bob"]}
    assert names(bob) == {"friends": [], "received": ["alice"], "sent": []}
    assert bob.get("/api/me").json["friendRequests"] == 1
    assert alice.get("/api/players/bob").json["friendship"] == "sent"
    assert bob.get("/api/players/alice").json["friendship"] == "received"

    assert bob.post("/api/friends/alice/accept").json["friendship"] == "friends"
    assert names(alice)["friends"] == ["bob"] and names(bob)["friends"] == ["alice"]
    assert bob.get("/api/me").json["friendRequests"] == 0
    friend = alice.get("/api/friends").json["friends"][0]
    assert friend["since"] and set(friend) >= {"name", "level", "ready", "colour"}


def test_asking_someone_who_asked_you_makes_you_friends(people):
    people["alice"].post("/api/friends", json={"player": "bob"})
    assert people["bob"].post("/api/friends", json={"player": "alice"}).json["friendship"] == "friends"
    assert names(people["alice"])["friends"] == ["bob"]


def test_requests_are_private_to_the_two_players(people):
    people["alice"].post("/api/friends", json={"player": "bob"})
    assert names(people["carol"]) == {"friends": [], "received": [], "sent": []}
    assert people["carol"].get("/api/players/bob").json["friendship"] == "none"
    # Only Bob can accept Alice's request.
    assert people["carol"].post("/api/friends/alice/accept").status_code == 404


def test_declining_cancelling_and_removing(people):
    alice, bob = people["alice"], people["bob"]
    alice.post("/api/friends", json={"player": "bob"})
    assert bob.delete("/api/friends/alice").status_code == 200  # declined
    assert names(alice)["sent"] == [] and names(bob)["received"] == []

    alice.post("/api/friends", json={"player": "bob"})
    assert alice.delete("/api/friends/bob").status_code == 200  # withdrawn
    assert names(bob)["received"] == []

    alice.post("/api/friends", json={"player": "bob"})
    bob.post("/api/friends/alice/accept")
    assert bob.delete("/api/friends/alice").status_code == 200  # no longer friends
    assert names(alice)["friends"] == [] and alice.delete("/api/friends/bob").status_code == 404


def test_asking_twice_changes_nothing(people):
    people["alice"].post("/api/friends", json={"player": "bob"})
    assert people["alice"].post("/api/friends", json={"player": "bob"}).json["friendship"] == "sent"
    assert names(people["bob"])["received"] == ["alice"]


@pytest.mark.parametrize("body, status", [
    ({"name": "Alice"}, 400),       # yourself
    ({"name": "Nobody"}, 404),
    ({}, 422),
])
def test_bad_requests(people, body, status):
    assert people["alice"].post("/api/friends", json=body).status_code == status


def test_profiles_are_public_but_the_list_of_players_is_not_a_screen(people):
    profile = people["alice"].get("/api/players/bob").json
    assert (profile["name"], profile["level"], profile["ready"], profile["you"]) == ("Bob", 1, False, False)
    assert "passwordHash" not in profile and "xp" not in profile
    assert people["alice"].get("/api/players/alice").json["friendship"] == "you"
    assert people["alice"].get("/api/players/nobody").status_code == 404


def test_deleting_a_player_ends_their_friendships(people, catalogue):
    people["alice"].post("/api/friends", json={"player": "bob"})
    people["bob"].post("/api/friends/alice/accept")
    people["carol"].post("/api/friends", json={"player": "bob"})
    catalogue.delete("players", "bob")
    assert names(people["alice"])["friends"] == [] and names(people["carol"])["sent"] == []
