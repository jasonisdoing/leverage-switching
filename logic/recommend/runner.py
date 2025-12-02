"""추천(신호) 생성 로직."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from logic.common.signals import compute_signals, pick_target
from logic.common.data import compute_bounds, download_prices
from utils.report import render_table_eaw


def run_recommend(settings: Dict) -> Dict[str, object]:
    start_bound, warmup_start, end_bound = compute_bounds(settings)

    prices_full = download_prices(settings, warmup_start)
    signal_df_full = compute_signals(prices_full[settings["signal_ticker"]], settings)
    valid_index = prices_full.index[prices_full.index >= start_bound]
    prices = prices_full.loc[valid_index]
    signal_df = signal_df_full.loc[valid_index]
    if signal_df.empty:
        raise ValueError("시그널 계산에 필요한 데이터가 없습니다.")
    last_date = signal_df.index.max()
    last_row = signal_df.loc[last_date]
    target = pick_target(last_row, settings)

    # 상태 계산: 타깃을 BUY, 나머지 WAIT
    offense = settings["trade_ticker"]
    defense = settings["defense_ticker"]
    assets = [offense]
    if defense != "CASH":
        assets.append(defense)

    # 테이블에 CASH 행을 항상 포함해 현금 보유 상태를 표시
    table_assets = ["CASH"] + assets if defense == "CASH" else assets

    statuses = {}
    if defense == "CASH":
        statuses["CASH"] = "HOLD" if target == "CASH" else "WAIT"
    for sym in assets:
        statuses[sym] = "BUY" if sym == target else "WAIT"

    # 일간 수익률은 전일 대비 종가 기준
    daily_rets = prices[assets].pct_change()
    last_ret = daily_rets.loc[last_date] if last_date in daily_rets.index else pd.Series(dtype=float)

    def _gap_message(row, price_today):
        dd_cut_raw = settings["drawdown_cutoff"]
        dd_cut = dd_cut_raw / 100 if dd_cut_raw > 1 else dd_cut_raw
        threshold = -dd_cut
        current_dd = row["drawdown"]

        # 드로다운이 임계값보다 낮아서(더 많이 떨어져서) 못 사는 경우
        if current_dd <= threshold:
            needed = threshold - current_dd
            return f"DD {current_dd*100:.2f}% (컷 {threshold*100:.2f}%, 필요 {needed*100:+.2f}%)"
        return ""

    # 테이블 구성
    headers = [
        "#",
        "티커",
        "상태",
        "보유일",
        "일간(%)",
        "현재가",
        "문구",
    ]
    aligns = ["center", "center", "center", "right", "right", "right", "left"]
    rows: List[List[str]] = []
    for idx, sym in enumerate(table_assets, start=1):
        if sym == "CASH":
            price = 1.0
            ret = 0.0
        else:
            price = prices.at[last_date, sym]
            ret = last_ret.get(sym, 0.0) if not last_ret.empty else 0.0
        note = ""
        if sym == target:
            note = "타깃"
        elif sym == offense:
            # offense 티커 문구에 추가 조건 설명
            note = _gap_message(last_row, price if sym != "CASH" else 1.0)
        elif sym == defense and defense != "CASH":
            note = "방어"
        rows.append(
            [
                str(idx),
                sym,
                statuses.get(sym, "WAIT"),
                "-",
                f"{ret*100:+.2f}%",
                f"{price:,.2f}",
                note,
            ]
        )

    table_lines = render_table_eaw(headers, rows, aligns)

    # 상태 요약
    status_counts = {}
    for st in statuses.values():
        status_counts[st] = status_counts.get(st, 0) + 1

    status_lines = ["=== 상태 요약 ==="]
    for st, cnt in status_counts.items():
        status_lines.append(f"  {st}: {cnt}개")

    return {
        "as_of": last_date.date().isoformat(),
        "target": target,
        "status_lines": status_lines,
        "table_lines": table_lines,
    }


def write_recommend_log(report: Dict, path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write(f"추천 로그 생성: {datetime.now().isoformat()}\n")
        f.write(f"기준일: {report['as_of']}\n\n")
        f.write("\n".join(report["status_lines"]))
        f.write("\n\n=== 추천 목록 ===\n\n")
        for line in report["table_lines"]:
            f.write(line + "\n")
