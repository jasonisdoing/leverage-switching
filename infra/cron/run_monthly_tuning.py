#!/usr/bin/env python3
"""월간 튜닝을 시장별로 순차 실행하는 배치 엔트리 포인트."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COUNTRIES = ("kor", "us")


def _run_country(country: str) -> int:
    command = [sys.executable, "tune.py", country, "--slack"]
    print(f"[run_monthly_tuning] 실행: {' '.join(command)}")
    result = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if result.returncode != 0:
        print(f"[run_monthly_tuning] 실패: {country.upper()} (exit={result.returncode})", file=sys.stderr)
    return result.returncode


def main() -> int:
    exit_code = 0
    for country in COUNTRIES:
        country_exit = _run_country(country)
        if country_exit != 0 and exit_code == 0:
            exit_code = country_exit
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
