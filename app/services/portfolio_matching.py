import unicodedata

_NUMBER_PRIZE_TIERS = {
    "megasena": {4: "quadra", 5: "quina", 6: "sena"},
    "lotofacil": {11: "11_acertos", 12: "12_acertos", 13: "13_acertos",
                  14: "14_acertos", 15: "15_acertos"},
    "quina": {2: "duque", 3: "terno", 4: "quadra", 5: "quina"},
    "diadesorte": {4: "4_acertos", 5: "5_acertos", 6: "6_acertos",
                    7: "7_acertos"},
}


def _normalized_text(value):
    if not isinstance(value, str):
        return None
    decomposed = unicodedata.normalize("NFKD", value.strip().casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def match_portfolio(portfolio, official_result):
    """Match saved games to one stored official result without inferring payouts."""
    if (
        portfolio["lottery"] != official_result["lottery"]
        or portfolio["contest"] != official_result["contest"]
    ):
        raise ValueError("portfolio_result_context_mismatch")

    lottery = portfolio["lottery"]
    drawn_numbers = set(official_result["numbers"])
    official_month = official_result["metadata"].get("mes_sorte")
    matches = []
    events = []

    for index, game in enumerate(portfolio["games"], start=1):
        hits = len(set(game["numbers"]) & drawn_numbers)
        number_tier = _NUMBER_PRIZE_TIERS[lottery].get(hits)
        lucky_month_match = None
        if lottery == "diadesorte":
            selected_month = (game.get("extra_selection") or {}).get("lucky_month")
            lucky_month_match = (
                official_month is not None
                and _normalized_text(selected_month) == _normalized_text(official_month)
            )

        match = {
            "game_number": index,
            "number_hits": hits,
            "number_prize_tier": number_tier,
            "lucky_month_match": lucky_month_match,
        }
        matches.append(match)
        if number_tier is not None or lucky_month_match:
            events.append({
                "type": "portfolio_game_match",
                "game_number": index,
                "number_hits": hits,
                "number_prize_tier": number_tier,
                "lucky_month_match": lucky_month_match,
                "message": f"Jogo {index:02d}: {hits} acertos",
            })

    return {
        "lottery": lottery,
        "contest": portfolio["contest"],
        "official_result": {
            "numbers": sorted(drawn_numbers),
            "lucky_month": official_month if lottery == "diadesorte" else None,
            "source": official_result["source"],
        },
        "games": matches,
        "events": events,
        "payouts": None,
        "payout_note": (
            "Valores de rateio não são inferidos. Só podem ser informados quando "
            "presentes no resultado oficial."
        ),
    }
