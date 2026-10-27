import sqlite3
import uuid
from datetime import datetime
import json


DATABASE_PATH = "app.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            sources TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
    """)

    columns = cursor.execute(
        "PRAGMA table_info(messages)"
    ).fetchall()

    column_names = [column["name"] for column in columns]

    if "sources" not in column_names:
        cursor.execute("""
            ALTER TABLE messages
            ADD COLUMN sources TEXT
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()
    
def create_conversation(title="New Conversation"):
    conversation_id = str(uuid.uuid4())

    created_at = datetime.utcnow().isoformat()

    connection = get_connection()

    connection.execute(
        """
        INSERT INTO conversations (id, title, created_at)
        VALUES (?, ?, ?)
        """,
        (conversation_id, title, created_at)
    )

    connection.commit()
    connection.close()

    return conversation_id

def conversation_exists(conversation_id):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT 1
        FROM conversations
        WHERE id = ?
        """,
        (conversation_id,)
    ).fetchone()

    connection.close()

    return row is not None

def get_conversations():
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT id, title, created_at
        FROM conversations
        ORDER BY created_at DESC
        """
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]


def add_message(
    conversation_id,
    role,
    content,
    sources=None
):
    message_id = str(uuid.uuid4())

    created_at = datetime.utcnow().isoformat()

    connection = get_connection()

    connection.execute(
        """
        INSERT INTO messages (
            id,
            conversation_id,
            role,
            content,
            sources,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            message_id,
            conversation_id,
            role,
            content,
            json.dumps(sources) if sources else None,
            created_at
        )
    )

    connection.commit()
    connection.close()

    return message_id


def get_messages(conversation_id):
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT id, role, content, sources, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY created_at ASC
        """,
        (conversation_id,)
    ).fetchall()

    connection.close()

    messages = []

    for row in rows:
        message = dict(row)

        if message["sources"]:
            message["sources"] = json.loads(message["sources"])
        else:
            message["sources"] = []

        messages.append(message)

    return messages
def get_recent_messages(conversation_id, limit=2):
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT id, role, content, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (conversation_id, limit)
    ).fetchall()

    connection.close()

    messages = [dict(row) for row in rows]

    messages.reverse()

    return messages

def create_document(
    document_id,
    filename,
    file_type,
    file_size
):
    created_at = datetime.utcnow().isoformat()

    connection = get_connection()

    connection.execute(
        """
        INSERT INTO documents (
            id,
            filename,
            file_type,
            file_size,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            document_id,
            filename,
            file_type,
            file_size,
            created_at
        )
    )

    connection.commit()
    connection.close()

    return document_id

def get_document(document_id):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT id, filename, file_type, file_size, created_at
        FROM documents
        WHERE id = ?
        """,
        (document_id,)
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return dict(row)
def get_documents():
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT id, filename, file_type, file_size, created_at
        FROM documents
        ORDER BY created_at DESC
        """
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]
    
def delete_document(document_id):
    connection = get_connection()

    connection.execute(
        """
        DELETE FROM documents
        WHERE id = ?
        """,
        (document_id,)
    )

    connection.commit()
    connection.close()
def update_conversation_title(conversation_id, title):
    connection = get_connection()

    connection.execute(
        """
        UPDATE conversations
        SET title = ?
        WHERE id = ?
        """,
        (title, conversation_id)
    )

    connection.commit()
    connection.close()

def delete_conversation(conversation_id):
    connection = get_connection()

    connection.execute(
        """
        DELETE FROM messages
        WHERE conversation_id = ?
        """,
        (conversation_id,)
    )

    cursor = connection.execute(
        """
        DELETE FROM conversations
        WHERE id = ?
        """,
        (conversation_id,)
    )

    connection.commit()
    connection.close()

    return cursor.rowcount > 0