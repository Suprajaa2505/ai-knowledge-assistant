"""SQLite layer - uses the real database functions."""
from app import database


def test_conversation_create_list_delete():
    conversation_id = database.create_conversation("My chat")

    assert database.conversation_exists(conversation_id)
    assert [c["title"] for c in database.get_conversations()] == ["My chat"]

    assert database.delete_conversation(conversation_id) is True
    assert not database.conversation_exists(conversation_id)


def test_messages_round_trip_with_sources():
    conversation_id = database.create_conversation()
    sources = [{"source": "a.pdf", "page": 2}]

    database.add_message(conversation_id, "user", "hi")
    database.add_message(conversation_id, "assistant", "hello", sources=sources)

    messages = database.get_messages(conversation_id)

    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["sources"] == []          # no sources -> empty list
    assert messages[1]["sources"] == sources     # JSON survives the round trip


def test_get_recent_messages_returns_last_n_in_order():
    conversation_id = database.create_conversation()
    for i in range(5):
        database.add_message(conversation_id, "user", f"message {i}")

    recent = database.get_recent_messages(conversation_id, limit=2)

    assert [m["content"] for m in recent] == ["message 3", "message 4"]


def test_deleting_conversation_deletes_its_messages():
    conversation_id = database.create_conversation()
    database.add_message(conversation_id, "user", "hi")

    database.delete_conversation(conversation_id)

    assert database.get_messages(conversation_id) == []


def test_document_record_round_trip():
    database.create_document("doc-1", "notes.txt", ".txt", 123)

    assert database.get_document("doc-1")["filename"] == "notes.txt"
    database.delete_document("doc-1")
    assert database.get_document("doc-1") is None

def test_failed_insert_does_not_lock_the_database():
    import sqlite3
    import pytest

    database.create_document("doc-1", "a.txt", ".txt", 1)

    with pytest.raises(sqlite3.IntegrityError):      # same id twice -> error
        database.create_document("doc-1", "a.txt", ".txt", 1)

    database.delete_document("doc-1")                 # must still work, no lock
    assert database.get_document("doc-1") is None