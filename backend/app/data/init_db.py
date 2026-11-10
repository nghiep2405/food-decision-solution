from __future__ import annotations

import argparse

from app.data.database import initialize_database


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the Food Decision SQLite schema.")
    parser.add_argument("--database", help="Optional target SQLite path.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete only the selected database file before creating the schema.",
    )
    args = parser.parse_args()
    path = initialize_database(args.database, reset=args.reset)
    print(f"Database initialized: {path}")


if __name__ == "__main__":
    main()
