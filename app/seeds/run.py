"""
CLI untuk menjalankan seed data.

Usage:
    python -m app.seeds run demo
    python -m app.seeds run admin --email admin@domain.com --password rahasia
    python -m app.seeds run all
"""

import argparse
import asyncio
import logging
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.seeds")
    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", help="Jalankan seed")
    run.add_argument(
        "target",
        choices=["demo", "admin", "all"],
        help="Target seed",
    )
    run.add_argument(
        "--email",
        default="admin@panitia.id",
        help="Admin email (untuk target admin)",
    )
    run.add_argument(
        "--password",
        default="admin12345",
        help="Admin password (untuk target admin)",
    )
    run.add_argument(
        "--name",
        default="Panitia Admin",
        help="Admin name (untuk target admin)",
    )

    args = parser.parse_args(argv)

    if args.command != "run":
        parser.print_help()
        return 0

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    asyncio.run(_run(args))

    return 0


async def _run(args) -> None:
    if args.target in ("demo", "all"):
        await _seed_demo()

    if args.target in ("admin", "all"):
        await _seed_admin(
            email=args.email,
            password=args.password,
            name=args.name,
        )


async def _seed_demo() -> None:
    from app.seeds.demo import seed_demo

    await seed_demo()


async def _seed_admin(email: str, password: str, name: str) -> None:
    from app.seeds.admin import seed_admin

    await seed_admin(
        email=email,
        password=password,
        name=name,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))