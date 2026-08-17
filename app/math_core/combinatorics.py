from dataclasses import dataclass
from math import comb

from app.lotteries.base import LotteryConfig


@dataclass(frozen=True)
class LotterySpace:
    slug: str
    minimum: int
    maximum: int
    draw_size: int

    @classmethod
    def from_config(cls, config: LotteryConfig):
        return cls(
            slug=config.slug,
            minimum=config.minimum,
            maximum=config.maximum,
            draw_size=config.quantity,
        )

    @property
    def population_size(self):
        return self.maximum - self.minimum + 1

    @property
    def total_outcomes(self):
        return comb(self.population_size, self.draw_size)

    def jackpot_probability(self, unique_games=1):
        unique_games = int(unique_games)

        if unique_games < 0:
            raise ValueError("unique_games_must_be_non_negative")

        if unique_games > self.total_outcomes:
            raise ValueError("unique_games_exceeds_outcome_space")

        return unique_games / self.total_outcomes

    def exact_hits_probability(self, hits):
        hits = int(hits)

        if hits < 0 or hits > self.draw_size:
            return 0.0

        misses = self.draw_size - hits
        non_ticket_numbers = self.population_size - self.draw_size

        if misses > non_ticket_numbers:
            return 0.0

        favorable = (
            comb(self.draw_size, hits)
            * comb(non_ticket_numbers, misses)
        )

        return favorable / self.total_outcomes
