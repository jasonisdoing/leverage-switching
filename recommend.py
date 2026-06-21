import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config import MARKET_SCHEDULES
from logic.backtest.runner import run_backtest
from logic.backtest.settings import load_settings
from logic.infinite_buy.runner import run_buy_backtest
from utils.slack import send_slack_buy_recommendation, send_slack_recommendation


def get_market_status(market: str) -> str:
    """현재 시간 기준 장 상태를 반환합니다.

    인자 market 은 MARKET_SCHEDULES 의 키(kor/us)입니다.

    반환값:
        "OPEN"            - 장중
        "CLOSED_JUST_NOW" - 장 마감 후 75분 이내
        "PRE_OPEN"        - 당일 장 시작 전
        "CLOSED"          - 장 마감 후 75분 초과 (전날 마감 이후 ~ 당일 개장 전 아닌 경우 포함)
    """
    from datetime import timedelta

    schedule = MARKET_SCHEDULES.get(market)
    if not schedule:
        return "OPEN"

    tz = ZoneInfo(schedule["timezone"])
    now = datetime.now(tz)

    # 주말 체크 (월=0, ..., 일=6)
    if now.weekday() >= 5:
        return "CLOSED"

    current_time = now.time()
    open_time = schedule["open"]
    close_time = schedule["close"]

    if open_time <= current_time <= close_time:
        return "OPEN"

    # 장 마감 후 75분 이내
    close_dt = datetime.combine(now.date(), close_time, tzinfo=tz)
    time_since_close = now - close_dt
    if timedelta(0) <= time_since_close <= timedelta(minutes=75):
        return "CLOSED_JUST_NOW"

    # 당일 개장 전
    open_dt = datetime.combine(now.date(), open_time, tzinfo=tz)
    if now < open_dt:
        return "PRE_OPEN"

    return "CLOSED"


MARKET_PHASE_LABEL = {
    "OPEN": "장중",
    "CLOSED_JUST_NOW": "장 마감 직후",
    "PRE_OPEN": "장전",
    "CLOSED": "장 마감 후",
}


def _market_label(market: str) -> str:
    return "🇺🇸 미국" if market == "us" else "🇰🇷 한국"


def load_previous_state(profile: str) -> dict:
    """저장된 이전 추천 상태를 로드합니다."""
    state_path = Path(f"state/last_recommendation_{profile}.json")
    if not state_path.exists():
        return {}
    try:
        with state_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_current_state(profile: str, state: dict) -> None:
    """현재 추천 상태를 저장합니다."""
    state_dir = Path("state")
    state_dir.mkdir(exist_ok=True)
    state_path = state_dir / f"last_recommendation_{profile}.json"
    with state_path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)


def _format_metric_pct(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value * 100:+.2f}%"


def _format_asset_price(value: float | None, prefix: str, suffix: str, fmt: str) -> str:
    if value is None:
        return "-"
    return f"{prefix}{format(value, fmt)}{suffix}"


def _format_display_name(ticker: str, name: str | None) -> str:
    if name and name != ticker:
        return f"{name}({ticker})"
    return ticker


def _build_ticker_names(settings: dict, prev_state: dict, display_target: str | None) -> dict[str, str]:
    ticker_names = {
        settings["offense_ticker"]: settings.get("offense_name", settings["offense_ticker"]),
        settings["defense_ticker"]: settings.get("defense_name", settings["defense_ticker"]),
        settings["signal_ticker"]: settings.get("signal_name", settings["signal_ticker"]),
    }

    for entry in settings.get("benchmarks", []):
        if isinstance(entry, dict):
            ticker = entry.get("ticker")
            name = entry.get("name")
            if ticker and name:
                ticker_names[ticker] = name

    if display_target and display_target not in ticker_names:
        ticker_names[display_target] = prev_state.get("target_name", display_target)

    return ticker_names


def main() -> None:
    parser = argparse.ArgumentParser(description="추천 실행 엔트리 포인트")
    parser.add_argument("profile", nargs="?", default="switch", help="전략 프로파일 (switch/buy)")
    parser.add_argument("--slack", action="store_true", help="결과를 Slack으로 전송")
    args = parser.parse_args()

    profile = args.profile
    config_path = Path(f"config/{profile}.json")
    if not config_path.exists():
        print(f"설정 파일을 찾을 수 없습니다: {config_path}")
        return

    settings = load_settings(config_path)
    market = settings.get("market", "kor")

    schedule = MARKET_SCHEDULES.get(market, {})
    tz_name = schedule.get("timezone", "UTC")
    now_local = datetime.now(ZoneInfo(tz_name)).strftime("%Y-%m-%d %H:%M %Z")
    status = get_market_status(market)
    market_phase = MARKET_PHASE_LABEL.get(status, "장 마감 후")
    print(f"[{profile}] 실행 시작 (현지시각: {now_local}, status: {status} [{market_phase}], slack={args.slack})")

    try:
        if settings["strategy"] == "buy":
            _recommend_buy(profile, settings, market, status, market_phase, args)
        else:
            _recommend_switch(profile, settings, market, status, market_phase, args)
    except Exception as exc:
        if "YFRateLimitError" in repr(exc) or "rate limit" in repr(exc).lower():
            print("YFRateLimitError: 요청이 너무 많습니다. 잠시 후 다시 실행하세요.")
            return
        raise


def _recommend_switch(profile: str, settings: dict, market: str, status: str, market_phase: str, args) -> None:
    is_warning = status == "OPEN"

    result = run_backtest(settings)

    # 마지막 날 추천 정보 추출
    last_target = result["last_target"]
    rec_data = result["recommendation_data"]
    end_date = rec_data["last_date"]

    # 이전 상태 로드 및 변경 여부 확인
    prev_state = load_previous_state(profile)
    prev_target = prev_state.get("target")
    is_changed = (prev_target is not None) and (prev_target != last_target)

    # 상태 저장: 장중이 아닐 때
    if status != "OPEN":
        current_state = {
            "date": end_date,
            "target": last_target,
            "target_name": settings.get(
                "offense_name" if last_target == settings["offense_ticker"] else "defense_name",
                last_target,
            ),
            "updated_at": datetime.now().isoformat(),
        }
        save_current_state(profile, current_state)

    if is_warning and prev_target is not None:
        display_target = prev_target
        warning_target = last_target if is_changed else None
    else:
        display_target = last_target
        warning_target = None

    offense_ticker = settings["offense_ticker"]
    offense_name = settings.get("offense_name", offense_ticker)
    defense_ticker = settings["defense_ticker"]
    defense_name = settings.get("defense_name", defense_ticker)

    last_prices = rec_data["last_prices"]
    daily_returns = rec_data.get("daily_returns", {})
    cum_returns = rec_data.get("cum_returns", {})
    current_dd = rec_data["current_drawdown"]
    buy_cutoff = rec_data["buy_cutoff"]
    sell_cutoff = rec_data["sell_cutoff"]
    needed_recovery = rec_data["needed_recovery"]

    if market == "kor":
        currency_prefix = ""
        currency_suffix = "원"
        price_fmt = ",.0f"
    else:
        currency_prefix = "$"
        currency_suffix = ""
        price_fmt = ",.2f"

    ticker_names = _build_ticker_names(settings, prev_state, display_target)

    pre_switch_data = result.get("pre_switch_data", {})
    pre_switch_hold_days = pre_switch_data.get("hold_days", {})
    pre_switch_cum_return = pre_switch_data.get("cum_return")

    table_lines = []
    assets = []
    if display_target and display_target not in (offense_ticker, defense_ticker):
        assets.append(display_target)
    for sym in [offense_ticker, defense_ticker]:
        if sym not in assets:
            assets.append(sym)

    for sym in assets:
        name = ticker_names.get(sym, sym)
        display_name = _format_display_name(sym, name)

        has_market_data = sym in last_prices
        price = last_prices.get(sym)
        day_ret = daily_returns.get(sym) if has_market_data else None
        c_ret = cum_returns.get(sym) if has_market_data else None

        if is_warning and warning_target and sym == display_target:
            if price is None:
                price = pre_switch_data.get("last_price")
            if day_ret is None:
                day_ret = pre_switch_data.get("daily_return")
            if pre_switch_cum_return is not None:
                c_ret = pre_switch_cum_return

        sell_cutoff_val = -sell_cutoff / 100
        needed_drop = (current_dd - sell_cutoff_val) * 100 if current_dd > sell_cutoff_val else 0

        if sym == display_target:
            status_text = "BUY"
            status_emoji = "✅️"
        else:
            status_text = "WAIT"
            status_emoji = "⏳️"

        signal_name = settings.get("signal", {}).get("name", "신호")
        note = ""
        if sym == offense_ticker:
            if display_target == offense_ticker:
                note = f"{signal_name}가 {needed_drop:.2f}% 더 하락 시 매도"
            elif warning_target == offense_ticker:
                note = f"{signal_name} 매수 조건 이미 충족 → 장 마감 후 매수 전환 예정"
            else:
                note = f"{signal_name}가 {needed_recovery:+.2f}% 더 회복 시 매수"
        else:
            note = ""

        table_lines.append(f"{status_emoji} {display_name}")
        table_lines.append(f"  상태: {status_text}")
        table_lines.append(f"  일간: {_format_metric_pct(day_ret)}")

        cum_text = f"  누적: {_format_metric_pct(c_ret)}"
        if sym == display_target:
            if is_warning and warning_target:
                h_days = pre_switch_hold_days.get(sym, 0)
            else:
                h_days = result.get("holding_days", 0)
            if h_days > 0:
                cum_text += f"({h_days}거래일째 보유중)"
        else:
            cum_text += "(미보유)"
        table_lines.append(cum_text)

        table_lines.append(f"  현재가: {_format_asset_price(price, currency_prefix, currency_suffix, price_fmt)}")
        if note:
            table_lines.append(f"  비고: {note}")
        table_lines.append("")

    target_name = ticker_names.get(display_target, display_target)
    target_display = _format_display_name(display_target, target_name)

    warning_target_display = None
    if warning_target:
        wt_name = ticker_names.get(warning_target, warning_target)
        warning_target_display = _format_display_name(warning_target, wt_name)

    out_dir = Path(f"zresults/{profile}")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"recommend_{datetime.now().date()}.log"

    with out_path.open("w", encoding="utf-8") as f:
        f.write(f"추천 로그 생성: {datetime.now().isoformat()}\n")
        f.write(f"프로파일: {profile} | 시장: {market}\n\n")
        f.write("=== 추천 목록 ===\n")
        for line in table_lines:
            f.write(line + "\n")
        f.write("\n")
        f.write(f"[INFO] 기준일: {end_date}\n")
        f.write(f"[INFO] 최종 타깃: {target_display}\n")
        f.write(f"[INFO] 적용 파라미터: {defense_ticker} / Buy {buy_cutoff}% / Sell {sell_cutoff}%\n")

    print(f"\n추천 결과 저장: {out_path}")

    if is_changed:
        print(f"⚠️ 포지션 변경 감지: {prev_target} -> {target_display}")
    else:
        print(f"ℹ️ 포지션 유지: {target_display}")

    market_name = _market_label(market)
    header_text = f"{market_name} 스위칭 {'포지션 변경 알림' if is_changed else '정기 보고'}"
    print("\n=== Slack 전송 요약 ===")
    print(f"{header_text} (기준일: {end_date})")
    print(f"🏆 최적 파라미터 (CAGR: {result.get('cagr', 0) * 100:.2f}%)")
    for line in table_lines:
        if line.strip():
            print(line.strip())
    print(f"🎯 최종 타깃: {target_display}")
    print("========================\n")

    if args.slack:
        tuning_meta = {
            "offense_ticker": offense_ticker,
            "offense_name": offense_name,
            "defense_ticker": defense_ticker,
            "defense_name": defense_name,
            "buy_cutoff": buy_cutoff,
            "sell_cutoff": sell_cutoff,
            "cagr": result.get("cagr", 0.0),
            "period_start": result.get("start"),
            "period_end": result.get("end"),
        }
        send_slack_recommendation(
            country=market,
            as_of=end_date,
            target_display=target_display,
            table_lines=table_lines,
            tuning_meta=tuning_meta,
            is_changed=is_changed,
            holding_days=result.get("holding_days", 0),
            is_warning=is_warning,
            warning_target_display=warning_target_display,
            market_phase=market_phase,
        )


def _recommend_buy(profile: str, settings: dict, market: str, status: str, market_phase: str, args) -> None:
    report = run_buy_backtest(settings)
    rec = report["recommendation"]
    end_date = report["end"]
    target_display = _format_display_name(settings["target_ticker"], settings["target_name"])

    prev_state = load_previous_state(profile)
    prev_action = prev_state.get("action")
    is_changed = (prev_action is not None) and (prev_action != rec["action"])

    if status != "OPEN":
        save_current_state(
            profile,
            {
                "date": end_date,
                "action": rec["action"],
                "buys_done": rec["buys_done"],
                "avg": rec["avg"],
                "updated_at": datetime.now().isoformat(),
            },
        )

    price_fmt = ",.0f" if market == "kor" else ",.2f"
    suffix = "원" if market == "kor" else ""

    def _p(v):
        return f"{format(v, price_fmt)}{suffix}" if v else "-"

    table_lines = [
        f"🎯 {target_display}",
        f"  오늘 행동: [{rec['action']}] {rec['message']}",
        f"  진행: {rec['buys_done']}/{rec['divisions']}회차",
        f"  평단: {_p(rec['avg'])}",
        f"  현재가(종가): {_p(rec['last_close'])}",
        f"  익절 목표가: {_p(rec['target_price'])}",
        f"  CAGR: {report['cagr'] * 100:.2f}% | MDD: {report['mdd'] * 100:.2f}% | 익절 {report['cycles']}회",
    ]

    out_dir = Path(f"zresults/{profile}")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"recommend_{datetime.now().date()}.log"
    with out_path.open("w", encoding="utf-8") as f:
        f.write(f"추천 로그 생성: {datetime.now().isoformat()}\n")
        f.write(f"프로파일: {profile}(무한매수법) | 시장: {market}\n\n")
        f.write("=== 추천 ===\n")
        for line in table_lines:
            f.write(line + "\n")
        f.write(f"\n[INFO] 기준일: {end_date}\n")

    print(f"\n추천 결과 저장: {out_path}")
    if is_changed:
        print(f"⚠️ 행동 변경 감지: {prev_action} -> {rec['action']}")
    else:
        print(f"ℹ️ 행동: {rec['action']}")

    print("\n=== Slack 전송 요약 ===")
    for line in table_lines:
        print(line)
    print("========================\n")

    if args.slack:
        send_slack_buy_recommendation(
            market=market,
            as_of=end_date,
            target_display=target_display,
            recommendation=rec,
            table_lines=table_lines,
            is_changed=is_changed,
            market_phase=market_phase,
        )


if __name__ == "__main__":
    main()
