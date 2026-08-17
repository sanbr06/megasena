import json
import sqlite3
from pathlib import Path


class ResultRepository:
    def __init__(self, database_url):
        self.path = self._resolve_path(database_url)

    def _resolve_path(self, url):
        if not url.startswith("sqlite:///"):
            raise ValueError("Only sqlite:/// is supported in this initial version")

        path = Path(url.removeprefix("sqlite:///"))
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    lottery TEXT NOT NULL,
                    contest INTEGER NOT NULL,
                    draw_date TEXT,
                    numbers TEXT NOT NULL,
                    source TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (lottery, contest)
                )
            """)

            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(results)").fetchall()
            }

            if "metadata" not in columns:
                conn.execute(
                    "ALTER TABLE results "
                    "ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'"
                )

            conn.commit()

    def save_result(
        self,
        lottery,
        contest,
        draw_date,
        numbers,
        source,
        metadata=None,
    ):
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO results(
                    lottery,
                    contest,
                    draw_date,
                    numbers,
                    source,
                    metadata
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(lottery, contest) DO UPDATE SET
                    draw_date=excluded.draw_date,
                    numbers=excluded.numbers,
                    source=excluded.source,
                    metadata=excluded.metadata
            """, (
                lottery,
                contest,
                draw_date,
                json.dumps(numbers),
                source,
                json.dumps(metadata or {}),
            ))
            conn.commit()

    def list_results(self, lottery, limit=None):
        query = """
            SELECT
                lottery,
                contest,
                draw_date,
                numbers,
                source,
                metadata,
                created_at
            FROM results
            WHERE lottery=?
            ORDER BY contest DESC
        """
        params = [lottery]

        if limit is not None:
            if limit <= 0:
                raise ValueError("limit_must_be_positive")

            query += " LIMIT ?"
            params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            {
                "lottery": row["lottery"],
                "contest": row["contest"],
                "draw_date": row["draw_date"],
                "numbers": json.loads(row["numbers"]),
                "source": row["source"],
                "metadata": json.loads(row["metadata"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def count_results(self, lottery):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total FROM results WHERE lottery=?",
                (lottery,),
            ).fetchone()

        return int(row["total"])
