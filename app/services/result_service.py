from app.lotteries import LOTTERIES


class ResultService:
    def __init__(self, repository, provider):
        self.repository = repository
        self.provider = provider

    def _persist(self, lottery, data):
        numbers = LOTTERIES[lottery].validate_numbers(data.get("dezenas", []))

        try:
            contest = int(data["concurso"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid_contest") from exc

        metadata = {}
        if data.get("mesSorte"):
            metadata["mes_sorte"] = data["mesSorte"]

        self.repository.save_result(
            lottery,
            contest,
            data.get("data"),
            numbers,
            self.provider.source_name,
            metadata=metadata,
        )
        return data

    def update_from_api(self, lottery):
        if lottery not in LOTTERIES:
            raise ValueError("unknown_lottery")

        return self._persist(lottery, self.provider.latest(lottery))

    def update_contest(self, lottery, contest):
        if lottery not in LOTTERIES:
            raise ValueError("unknown_lottery")

        return self._persist(
            lottery,
            self.provider.by_contest(lottery, contest),
        )

    def history(self, lottery, limit=None):
        if lottery not in LOTTERIES:
            raise ValueError("unknown_lottery")
        return self.repository.list_results(lottery, limit=limit)
