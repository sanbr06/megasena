from app.lotteries import LOTTERIES


class ResultService:
    def __init__(self, repository, provider):
        self.repository = repository
        self.provider = provider

    def update_from_api(self, lottery):
        if lottery not in LOTTERIES:
            raise ValueError("unknown_lottery")

        data = self.provider.latest(lottery)
        numbers = LOTTERIES[lottery].validate_numbers(data.get("dezenas", []))

        try:
            contest = int(data["concurso"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid_contest") from exc

        self.repository.save_result(
            lottery,
            contest,
            data.get("data"),
            numbers,
            self.provider.source_name,
        )
        return data

    def history(self, lottery, limit=None):
        if lottery not in LOTTERIES:
            raise ValueError("unknown_lottery")
        return self.repository.list_results(lottery, limit=limit)
