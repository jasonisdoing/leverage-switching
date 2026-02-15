"""Configuration defaults for strategy backtests."""

from datetime import time

# Simulation start date (inclusive) in YYYY-MM-DD format.
# Feel free to change this to the date you want your backtests to begin.
SIMULATION_START_DATE = "2020-01-01"

INITIAL_CAPITAL_KRW = 10_000_000

MARKET_SCHEDULES = {
    "kor": {
        "open": time(9, 0),
        "close": time(15, 30),
        "timezone": "Asia/Seoul",
    },
    "us": {
        "open": time(9, 30),
        "close": time(16, 0),
        "timezone": "America/New_York",
    },
}
