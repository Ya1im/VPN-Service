import json
import uuid

import pytest

from vpn.store import UserStore


def test_missing_file_gives_empty_list(tmp_path):
    assert UserStore(tmp_path / "users.json").list() == []


def test_add_generates_uuid_and_long_token(tmp_path):
    store = UserStore(tmp_path / "users.json")
    u = store.add("mom")
    uuid.UUID(u.uuid)  # valid uuid
    assert len(u.sub_token) >= 32
    assert u.active is True
    # persisted and reloadable
    assert [x.name for x in UserStore(tmp_path / "users.json").list()] == ["mom"]


def test_duplicate_name_rejected(tmp_path):
    store = UserStore(tmp_path / "users.json")
    store.add("mom")
    with pytest.raises(ValueError):
        store.add("mom")


def test_revoke_deactivates_and_hides_token(tmp_path):
    store = UserStore(tmp_path / "users.json")
    u = store.add("dad")
    assert store.by_token(u.sub_token).name == "dad"
    assert store.revoke("dad") is True
    assert store.by_token(u.sub_token) is None
    assert store.revoke("nobody") is False
    assert [x.active for x in store.list()] == [False]


def test_write_is_atomic_and_corrupt_file_tolerated(tmp_path):
    p = tmp_path / "users.json"
    p.write_text("{not json")
    store = UserStore(p)
    assert store.list() == []
    store.add("x")
    assert json.loads(p.read_text())[0]["name"] == "x"
    assert not list(tmp_path.glob("*.tmp"))


def test_invalid_names_rejected(tmp_path):
    store = UserStore(tmp_path / "users.json")
    for bad in ["", "a b", "x" * 33, "имя#"]:
        with pytest.raises(ValueError):
            store.add(bad)


def test_by_token_with_garbage_returns_none(tmp_path):
    store = UserStore(tmp_path / "users.json")
    store.add("x")
    assert store.by_token("тест") is None
    assert store.by_token("") is None
