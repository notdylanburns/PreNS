import sqlite3
from typing import Self

from src.host import Host

TABLES = {
    "hostname": [
        """
            CREATE TABLE IF NOT EXISTS hostname (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostname VARCHAR(255) UNIQUE NOT NULL,
                ttl INTEGER NOT NULL,
                updated_at TIMESTAMP,
                resolved_at TIMESTAMP,
                error_message VARCHAR(255)
            );
        """
    ],
    "heirarchy": [
        """
            CREATE TABLE IF NOT EXISTS heirarchy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) UNIQUE NOT NULL,
                parent INTEGER REFERENCES heirarchy(id),
                hostname_id INTEGER REFERENCES hostname(id)
            );
        """,
        "CREATE INDEX IF NOT EXISTS idx_heirarchy_parent ON heirarchy(parent);",
    ],
}


class Database:
    class Conn:
        def __init__(self, conn: sqlite3.Connection):
            self.conn = conn

        def __enter__(self) -> Self:
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            if self.conn:
                self.conn.close()

        def get_table_names(self) -> list[str]:
            return [
                row[0]
                for row in self.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table';"
                ).fetchall()
            ]

        def initialise_tables(self):
            existing_tables = self.get_table_names()

            for table in TABLES.values():
                if table in existing_tables:
                    continue

                for query in table:
                    self.conn.execute(query)

        def insert_host(self, host: Host) -> dict:
            cursor = self.conn.cursor()
            hostname_id = cursor.execute(
                """
                    INSERT INTO hostname (hostname, ttl)
                    VALUES (?, ?)
                    ON CONFLICT(hostname) DO UPDATE SET ttl=excluded.ttl
                    RETURNING id;
                """,
                (host.hostname, host.ttl),
            ).fetchone()[0]

            parent = None
            for prefix in host.get_prefixes():
                existing_row = cursor.execute(
                    "SELECT id FROM heirarchy WHERE name = ?;", (prefix,)
                ).fetchone()
                if existing_row is None:
                    parent = cursor.execute(
                        "INSERT INTO heirarchy (name, parent) VALUES (?, ?) RETURNING id;",
                        (prefix, parent),
                    ).fetchone()[0]
                else:
                    parent = existing_row[0]

            cursor.execute(
                """
                    INSERT INTO heirarchy (name, parent, hostname_id)
                    VALUES (?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET hostname_id=excluded.hostname_id;
                """,
                (host.hostname, parent, hostname_id),
            )

            self.conn.commit()

            return {
                "id": hostname_id,
                "hostname": host.hostname,
                "ttl": host.ttl,
            }

        def get_hosts(self, after: int = -1, page_size: int = 100) -> list[dict]:
            rows = self.conn.execute(
                """
                    SELECT
                        id,
                        hostname,
                        ttl,
                        resolved_at,
                        error_message
                    FROM hostname
                    WHERE id > ?
                    LIMIT ?;
                """,
                (after, page_size),
            ).fetchall()

            return [
                {
                    "id": row[0],
                    "hostname": row[1],
                    "ttl": row[2],
                    "resolved_at": row[3],
                    "error_message": row[4],
                }
                for row in rows
            ]

        def get_children(self, parent: int | None = None) -> list[dict]:
            children = self.conn.execute(
                """
                    SELECT
                        id,
                        name,
                        hostname_id
                    FROM heirarchy
                    WHERE parent IS ?;
                """,
                (parent,),
            ).fetchall()

            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "hostname_id": row[2],
                }
                for row in children
            ]

        def delete_host(self, id: int):
            with self.conn:
                self.conn.execute("DELETE FROM hostname WHERE id = ?", (id,))
                self.conn.execute(
                    "UPDATE heirarchy SET hostname_id = NULL WHERE hostname_id = ?",
                    (id,),
                )

        def heirarchy_cleanup(self) -> list[int]:
            removed = set()
            while True:
                with self.conn:
                    ids = self.conn.execute(
                        """
                            SELECT DISTINCT h1.id
                            FROM heirarchy h1
                            LEFT JOIN heirarchy h2
                            ON h1.id = h2.parent
                            WHERE h1.hostname_id IS NULL
                            AND h2.id IS NULL;
                        """
                    ).fetchall()

                    ids = [id[0] for id in ids]
                    if not ids:
                        break

                    removed.update(ids)

                    id_string = ",".join(str(id) for id in ids)
                    self.conn.execute(
                        f"DELETE FROM heirarchy WHERE id IN ({id_string})"
                    )

            return sorted(removed)

        def close(self):
            self.conn.commit()
            self.conn.close()

    path: str
    conn: Conn | None

    def __init__(self, path: str):
        self.path = path
        self.conn = None

    def connect(self) -> Conn:
        return self.Conn(sqlite3.connect(self.path))
