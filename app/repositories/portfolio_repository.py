import json


class PortfolioRepository:
    """Persist user portfolios separately from official lottery results."""

    def __init__(self, connection_factory):
        self._connect = connection_factory

    def initialize(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS saved_portfolios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lottery TEXT NOT NULL,
                    contest INTEGER NOT NULL,
                    games TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    strategy_version TEXT NOT NULL,
                    strategy_parameters TEXT NOT NULL,
                    seed INTEGER NOT NULL,
                    pricing_version TEXT NOT NULL,
                    simple_game_cost_cents INTEGER NOT NULL,
                    total_cost_cents INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def save(self, portfolio):
        with self._connect() as conn:
            cursor = conn.execute("""
                INSERT INTO saved_portfolios (
                    lottery, contest, games, strategy_name, strategy_version,
                    strategy_parameters, seed, pricing_version,
                    simple_game_cost_cents, total_cost_cents, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                portfolio["lottery"],
                portfolio["contest"],
                json.dumps(portfolio["games"], separators=(",", ":")),
                portfolio["strategy"]["name"],
                portfolio["strategy"]["version"],
                json.dumps(
                    portfolio["strategy"]["parameters"],
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                portfolio["seed"],
                portfolio["cost_snapshot"]["pricing_version"],
                portfolio["cost_snapshot"]["simple_game_cost_cents"],
                portfolio["cost_snapshot"]["total_cost_cents"],
                "saved",
            ))
            portfolio_id = cursor.lastrowid
            conn.commit()
        return self.get(portfolio_id)

    def get(self, portfolio_id):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM saved_portfolios WHERE id=?",
                (portfolio_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "lottery": row["lottery"],
            "contest": row["contest"],
            "games": json.loads(row["games"]),
            "strategy": {
                "name": row["strategy_name"],
                "version": row["strategy_version"],
                "parameters": json.loads(row["strategy_parameters"]),
            },
            "seed": row["seed"],
            "cost_snapshot": {
                "pricing_version": row["pricing_version"],
                "simple_game_cost_cents": row["simple_game_cost_cents"],
                "total_cost_cents": row["total_cost_cents"],
            },
            "status": row["status"],
            "created_at": row["created_at"],
        }

    def list_recent(self, limit=50):
        limit = max(1, min(int(limit), 100))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id FROM saved_portfolios ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self.get(row["id"]) for row in rows]

    def update_status(self, portfolio_id, status):
        with self._connect() as conn:
            conn.execute(
                "UPDATE saved_portfolios SET status=? WHERE id=?",
                (status, portfolio_id),
            )
            conn.commit()
        return self.get(portfolio_id)
