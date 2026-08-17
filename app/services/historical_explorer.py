from datetime import datetime

from app.lotteries import LOTTERIES


def _parse_draw_date(value):
    if not value:
        return None
    for date_format in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    return None


def _number_bands(config):
    return [
        (start, min(start + 9, config.maximum))
        for start in range(config.minimum, config.maximum + 1, 10)
    ]


def explore_history(
    results,
    lottery,
    *,
    contest_from=None,
    contest_to=None,
    date_from=None,
    date_to=None,
):
    """Build descriptive metrics from stored draws, never a predictive score."""
    config = LOTTERIES[lottery]
    selected = []
    for result in results:
        draw_date = _parse_draw_date(result["draw_date"])
        if contest_from is not None and result["contest"] < contest_from:
            continue
        if contest_to is not None and result["contest"] > contest_to:
            continue
        if date_from is not None and (draw_date is None or draw_date < date_from):
            continue
        if date_to is not None and (draw_date is None or draw_date > date_to):
            continue
        selected.append((result, draw_date))

    selected.sort(key=lambda item: item[0]["contest"])
    frequencies = {number: 0 for number in range(config.minimum, config.maximum + 1)}
    last_seen_index = {}
    previous_numbers = set()
    draws = []
    bands = _number_bands(config)

    for index, (result, draw_date) in enumerate(selected):
        numbers = sorted(result["numbers"])
        number_set = set(numbers)
        for number in numbers:
            frequencies[number] += 1
            last_seen_index[number] = index
        draws.append({
            "contest": result["contest"],
            "draw_date": draw_date.isoformat() if draw_date else result["draw_date"],
            "numbers": numbers,
            "odd_count": sum(number % 2 for number in numbers),
            "even_count": sum(number % 2 == 0 for number in numbers),
            "sum": sum(numbers),
            "repeated_from_previous": len(number_set & previous_numbers) if index else None,
            "band_counts": [
                {
                    "start": start,
                    "end": end,
                    "count": sum(start <= number <= end for number in numbers),
                }
                for start, end in bands
            ],
        })
        previous_numbers = number_set

    draw_count = len(selected)
    number_metrics = [
        {
            "number": number,
            "frequency": frequency,
            "draws_since_last_seen": (
                draw_count - 1 - last_seen_index[number]
                if number in last_seen_index
                else None
            ),
        }
        for number, frequency in frequencies.items()
    ]
    return {
        "lottery": lottery,
        "draw_count": draw_count,
        "filters": {
            "contest_from": contest_from,
            "contest_to": contest_to,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
        },
        "number_metrics": number_metrics,
        "draws": draws,
        "disclaimer": "Dados históricos descritivos; não são previsão de sorteios futuros.",
    }
