from dataclasses import dataclass


@dataclass(frozen=True)
class LotteryConfig:
    slug: str
    minimum: int
    maximum: int
    quantity: int

    def validate_numbers(self, numbers):
        values = sorted({int(n) for n in numbers})
        if len(values) != self.quantity:
            raise ValueError(f"{self.slug}: expected {self.quantity} unique numbers")
        if any(n < self.minimum or n > self.maximum for n in values):
            raise ValueError(f"{self.slug}: number outside valid range")
        return values
