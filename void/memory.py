import sqlite3
import os
from datetime import datetime


class Memory:

    def __init__(self, path="data/memory.db"):

        directory = os.path.dirname(path)

        if directory:
            os.makedirs(directory, exist_ok=True)

        self.db = sqlite3.connect(path)

        self.db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        self.db.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            importance INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        self.db.execute("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT NOT NULL,
            source TEXT,
            category TEXT DEFAULT 'general',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        self.db.commit()

    # --------------------------------------------------
    # Conversation memory
    # --------------------------------------------------

    def add(self, role, content):

        self.db.execute(
            """
            INSERT INTO messages(role, content)
            VALUES (?, ?)
            """,
            (role, content)
        )

        self.db.commit()

    def recent(self, limit=20):

        rows = self.db.execute(
            """
            SELECT role, content
            FROM messages
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

        return list(reversed(rows))

    # --------------------------------------------------
    # Long-term memory
    # --------------------------------------------------

    def remember(
        self,
        content,
        category="general",
        importance=1
    ):

        self.db.execute(
            """
            INSERT INTO memories(
                category,
                content,
                importance
            )
            VALUES (?, ?, ?)
            """,
            (
                category,
                content,
                importance
            )
        )

        self.db.commit()

    def get_memories(
        self,
        category=None,
        limit=20
    ):

        if category:

            rows = self.db.execute(
                """
                SELECT id, category, content,
                       importance, created_at, updated_at
                FROM memories
                WHERE category = ?
                ORDER BY importance DESC, id DESC
                LIMIT ?
                """,
                (
                    category,
                    limit
                )
            ).fetchall()

        else:

            rows = self.db.execute(
                """
                SELECT id, category, content,
                       importance, created_at, updated_at
                FROM memories
                ORDER BY importance DESC, id DESC
                LIMIT ?
                """,
                (limit,)
            ).fetchall()

        return rows

    def search_memory(
        self,
        query,
        limit=10
    ):

        pattern = f"%{query}%"

        rows = self.db.execute(
            """
            SELECT id, category, content,
                   importance, created_at, updated_at
            FROM memories
            WHERE content LIKE ?
               OR category LIKE ?
            ORDER BY importance DESC, id DESC
            LIMIT ?
            """,
            (
                pattern,
                pattern,
                limit
            )
        ).fetchall()

        return rows

    def forget_memory(self, memory_id):

        self.db.execute(
            """
            DELETE FROM memories
            WHERE id = ?
            """,
            (memory_id,)
        )

        self.db.commit()

    # --------------------------------------------------
    # Knowledge base
    # --------------------------------------------------

    def add_knowledge(
        self,
        content,
        title="",
        source="",
        category="general"
    ):

        self.db.execute(
            """
            INSERT INTO knowledge(
                title,
                content,
                source,
                category
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                title,
                content,
                source,
                category
            )
        )

        self.db.commit()

    def search_knowledge(
        self,
        query,
        limit=10
    ):

        pattern = f"%{query}%"

        rows = self.db.execute(
            """
            SELECT id,
                   title,
                   content,
                   source,
                   category,
                   created_at
            FROM knowledge
            WHERE title LIKE ?
               OR content LIKE ?
               OR source LIKE ?
               OR category LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                pattern,
                pattern,
                pattern,
                pattern,
                limit
            )
        ).fetchall()

        return rows

    def get_knowledge(
        self,
        category=None,
        limit=20
    ):

        if category:

            rows = self.db.execute(
                """
                SELECT id,
                       title,
                       content,
                       source,
                       category,
                       created_at
                FROM knowledge
                WHERE category = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    category,
                    limit
                )
            ).fetchall()

        else:

            rows = self.db.execute(
                """
                SELECT id,
                       title,
                       content,
                       source,
                       category,
                       created_at
                FROM knowledge
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,)
            ).fetchall()

        return rows

    def delete_knowledge(self, knowledge_id):

        self.db.execute(
            """
            DELETE FROM knowledge
            WHERE id = ?
            """,
            (knowledge_id,)
        )

        self.db.commit()

    # --------------------------------------------------
    # Statistics
    # --------------------------------------------------

    def stats(self):

        messages = self.db.execute(
            "SELECT COUNT(*) FROM messages"
        ).fetchone()[0]

        memories = self.db.execute(
            "SELECT COUNT(*) FROM memories"
        ).fetchone()[0]

        knowledge = self.db.execute(
            "SELECT COUNT(*) FROM knowledge"
        ).fetchone()[0]

        return {
            "messages": messages,
            "memories": memories,
            "knowledge": knowledge
        }

    # --------------------------------------------------
    # Clear conversation only
    # --------------------------------------------------

    def clear(self):

        self.db.execute(
            "DELETE FROM messages"
        )

        self.db.commit()

    # --------------------------------------------------
    # Close database
    # --------------------------------------------------

    def close(self):

        self.db.close()
