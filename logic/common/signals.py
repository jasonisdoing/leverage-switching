"""공통 시그널 계산 및 포지션 선택 로직."""

from typing import Dict

import numpy as np
import pandas as pd


def compute_signals(prices: pd.Series, settings: Dict) -> pd.DataFrame:
    """가격 시계열로 추세/변동성/드로다운 신호를 계산합니다."""
    df = pd.DataFrame(index=prices.index)
    df["close"] = prices
    df["ma_short"] = prices.rolling(settings["ma_short"]).mean()
    df["ma_long"] = prices.rolling(settings["ma_long"]).mean()
    df["vol"] = prices.pct_change().rolling(settings["vol_lookback"]).std() * np.sqrt(252)
    peak = prices.cummax()
    df["drawdown"] = prices / peak - 1.0
    return df.dropna()


def pick_target(row, settings: Dict) -> str:
    """신호 행을 받아 매수 대상 티커를 결정합니다."""
    vol_cutoff_raw = settings["vol_cutoff"]
    vol_cutoff = vol_cutoff_raw / 100 if vol_cutoff_raw > 1 else vol_cutoff_raw
    dd_cutoff_raw = settings["drawdown_cutoff"]
    dd_cutoff = dd_cutoff_raw / 100 if dd_cutoff_raw > 1 else dd_cutoff_raw

    if row["drawdown"] <= -dd_cutoff:
        return "QQQM"
    if row["ma_short"] > row["ma_long"] and row["vol"] < vol_cutoff:
        return "TQQQ"
    if row["ma_short"] > row["ma_long"]:
        return "QLD"
    return "QQQM"
