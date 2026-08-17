import requests

from app.lotteries import LOTTERIES


class ResultService:
    def __init__(self, repository, timeout=15):
        self.repository = repository
        self.timeout = timeout

    def update_from_api(self, lottery):
        if lottery not in LOTTERIES:
            raise ValueError("unknown_lottery")

        url = f"https://loteriascaixa-api.herokuapp.com/api/{lottery}/latest"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        numbers = LOTTERIES[lottery].validate_numbers(data.get("dezenas", []))
        contest = int(data["concurso"])

        self.repository.save_result(
            lottery,
            contest,
            data.get("data"),
            numbers,
            url,
        )
        return data

    def history(self, lottery):
        if lottery not in LOTTERIES:
            raise ValueError("unknown_lottery")
        return self.repository.list_results(lottery)
