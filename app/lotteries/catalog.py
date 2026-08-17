from dataclasses import asdict, dataclass

from app.lotteries import LOTTERIES

PRICING_VERSION = "caixa-2026-08-17"


@dataclass(frozen=True)
class ExtraSelection:
    key: str
    label: str
    quantity: int
    options: tuple[str, ...]


@dataclass(frozen=True)
class LotteryProduct:
    slug: str
    name: str
    minimum_number: int
    maximum_number: int
    draw_size: int
    simple_game_cost_cents: int
    pricing_version: str
    extra_selection: ExtraSelection | None = None


_LUCKY_MONTHS = (
    "janeiro",
    "fevereiro",
    "marco",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)

_PRODUCT_DETAILS = {
    "megasena": ("Mega-Sena", 600, None),
    "lotofacil": ("Lotofácil", 350, None),
    "quina": ("Quina", 300, None),
    "diadesorte": (
        "Dia de Sorte",
        250,
        ExtraSelection(
            key="lucky_month",
            label="Mês de Sorte",
            quantity=1,
            options=_LUCKY_MONTHS,
        ),
    ),
}


def lottery_product_catalog():
    products = []
    for slug, (name, cost_cents, extra_selection) in _PRODUCT_DETAILS.items():
        config = LOTTERIES[slug]
        products.append(LotteryProduct(
            slug=slug,
            name=name,
            minimum_number=config.minimum,
            maximum_number=config.maximum,
            draw_size=config.quantity,
            simple_game_cost_cents=cost_cents,
            pricing_version=PRICING_VERSION,
            extra_selection=extra_selection,
        ))
    return products


def lottery_product_catalog_as_dict():
    return [asdict(product) for product in lottery_product_catalog()]
