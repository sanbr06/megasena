import random

from app.lotteries import LOTTERIES


class LotteryService:
    def __init__(self, repository):
        self.repository = repository

    def _frequency(self, lottery):
        config = LOTTERIES[lottery]
        frequency = {n: 0 for n in range(config.minimum, config.maximum + 1)}

        for result in self.repository.list_results(lottery):
            for number in result["numbers"]:
                if number in frequency:
                    frequency[number] += 1

        return frequency

    def generate(self, lottery):
        if lottery not in LOTTERIES:
            raise ValueError("unknown_lottery")

        config = LOTTERIES[lottery]
        frequency = self._frequency(lottery)
        population = list(range(config.minimum, config.maximum + 1))

        if not any(frequency.values()):
            return sorted(random.sample(population, config.quantity))

        weights = [1 + frequency[n] for n in population]
        selected = set()

        while len(selected) < config.quantity:
            selected.add(random.choices(population, weights=weights, k=1)[0])

        return sorted(selected)

    def stats(self, lottery):
        if lottery not in LOTTERIES:
            raise ValueError("unknown_lottery")

        frequency = self._frequency(lottery)
        ordered = sorted(frequency.items(), key=lambda item: (-item[1], item[0]))

        return {
            "lottery": lottery,
            "draws": self.repository.count_results(lottery),
            "frequency": dict(ordered),
            "top_numbers": ordered[:10],
        }

    def train(self, lottery):
        stats = self.stats(lottery)
        return {
            "lottery": lottery,
            "status": "statistics_refreshed",
            "draws_used": stats["draws"],
            "algorithm": "frequency_weighted_v1",
            "model_type": "heuristic",
            "top_numbers": stats["top_numbers"],
        }
