"""宇宙文明模拟器 — 主入口"""
from __future__ import annotations

import sys

from src.cli import main as cli_main


def main() -> None:
    sys.exit(cli_main())


if __name__ == "__main__":
    main()
