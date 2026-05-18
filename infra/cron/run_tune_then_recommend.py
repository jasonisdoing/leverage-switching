#!/usr/bin/env python3
"""튜닝 후 추천을 순서대로 실행하는 배치 엔트리 포인트."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

SUPPORTED_COUNTRIES = ("kor", "us")


def _run_step(command: list[str]) -> int:
    print(f"[run_tune_then_recommend] 실행: {' '.join(command)}")
    result = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if result.returncode != 0:
        print(f"[run_tune_then_recommend] 실패: {' '.join(command)} (exit={result.returncode})", file=sys.stderr)
    return result.returncode


def _validate_tuned_config(country: str) -> None:
    """튜닝 결과가 현재 탐색 상한을 넘지 않는지 확인한다."""
    from tune import TUNING_CONFIG

    tuning_config = TUNING_CONFIG[country]
    max_buy = float(max(tuning_config["drawdown_buy_cutoff"]))
    max_sell = float(max(tuning_config["drawdown_sell_cutoff"]))

    config_path = PROJECT_ROOT / "config" / f"{country}.json"
    with config_path.open(encoding="utf-8") as f:
        config = json.load(f)

    buy_cutoff = float(config["drawdown_buy_cutoff"])
    sell_cutoff = float(config["drawdown_sell_cutoff"])
    if buy_cutoff > max_buy or sell_cutoff > max_sell:
        raise ValueError(
            f"튜닝 결과가 탐색 상한을 초과했습니다: "
            f"buy={buy_cutoff} (max={max_buy}), sell={sell_cutoff} (max={max_sell})"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="튜닝 후 추천 실행")
    parser.add_argument("country", choices=SUPPORTED_COUNTRIES, help="대상 국가")
    parser.add_argument("--slack", action="store_true", help="추천 결과를 Slack으로 전송")
    args = parser.parse_args()

    python = sys.executable
    tune_code = _run_step([python, "tune.py", args.country])
    if tune_code != 0:
        return tune_code

    try:
        _validate_tuned_config(args.country)
    except Exception as exc:
        print(f"[run_tune_then_recommend] 튜닝 결과 검증 실패: {exc}", file=sys.stderr)
        return 1

    recommend_command = [python, "recommend.py", args.country]
    if args.slack:
        recommend_command.append("--slack")
    return _run_step(recommend_command)


if __name__ == "__main__":
    raise SystemExit(main())
