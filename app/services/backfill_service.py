import time

from app.lotteries import LOTTERIES


class BackfillService:
    def __init__(self, repository, result_service, provider, sleep_fn=time.sleep):
        self.repository = repository
        self.result_service = result_service
        self.provider = provider
        self.sleep_fn = sleep_fn

    def backfill(self, lottery, start=1, end=None, delay=0.10, on_progress=None):
        if lottery not in LOTTERIES:
            raise ValueError("unknown_lottery")

        start = int(start)
        if start <= 0:
            raise ValueError("invalid_start")

        if end is None:
            end = int(self.provider.latest(lottery)["concurso"])
        else:
            end = int(end)

        if end < start:
            raise ValueError("invalid_range")

        existing = {
            item["contest"]
            for item in self.repository.list_results(lottery)
        }

        inserted = 0
        skipped = 0

        for contest in range(start, end + 1):
            if contest in existing:
                skipped += 1
                if on_progress:
                    on_progress(lottery, contest, "skipped")
                continue

            self.result_service.update_contest(lottery, contest)
            inserted += 1

            if on_progress:
                on_progress(lottery, contest, "saved")

            if delay > 0 and contest < end:
                self.sleep_fn(delay)

        return {
            "lottery": lottery,
            "start": start,
            "end": end,
            "inserted": inserted,
            "skipped": skipped,
            "total": end - start + 1,
        }
