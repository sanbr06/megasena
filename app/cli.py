import argparse

from app import create_app
from app.lotteries import LOTTERIES
from app.services.backfill_service import BackfillService


def _progress(lottery, contest, status):
    print(f"{lottery:12} concurso={contest:<6} {status}")


def main():
    parser = argparse.ArgumentParser(description="MegaSena Intelligence CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backfill = subparsers.add_parser(
        "backfill",
        help="Carrega concursos históricos da CAIXA",
    )
    backfill.add_argument(
        "--lottery",
        choices=[*LOTTERIES.keys(), "all"],
        required=True,
    )
    backfill.add_argument("--start", type=int, default=1)
    backfill.add_argument("--end", type=int)
    backfill.add_argument("--delay", type=float, default=0.10)

    args = parser.parse_args()

    if args.command == "backfill":
        app = create_app()

        repository = app.extensions["result_repository"]
        provider = app.extensions["lottery_provider"]
        result_service = app.extensions["result_service"]

        service = BackfillService(
            repository,
            result_service,
            provider,
        )

        lotteries = (
            list(LOTTERIES)
            if args.lottery == "all"
            else [args.lottery]
        )

        for lottery in lotteries:
            summary = service.backfill(
                lottery,
                start=args.start,
                end=args.end,
                delay=args.delay,
                on_progress=_progress,
            )
            print(
                f"{lottery}: "
                f"salvos={summary['inserted']} "
                f"existentes={summary['skipped']} "
                f"total={summary['total']}"
            )


if __name__ == "__main__":
    main()
