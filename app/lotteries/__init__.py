from app.lotteries.base import LotteryConfig

LOTTERIES = {
    "megasena": LotteryConfig("megasena", 1, 60, 6),
    "lotofacil": LotteryConfig("lotofacil", 1, 25, 15),
    "quina": LotteryConfig("quina", 1, 80, 5),
    "diadesorte": LotteryConfig("diadesorte", 1, 31, 7),
}
