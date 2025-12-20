"""추천 실행 엔트리 포인트.

백테스트 결과의 마지막 날 데이터를 "오늘의 추천"으로 출력합니다.
"""

from datetime import datetime
from pathlib import Path

from logic.backtest.runner import run_backtest
from logic.backtest.settings import load_settings


def main() -> None:
    settings_path = Path("settings.json")
    settings = load_settings(settings_path)

    try:
        result = run_backtest(settings)
    except Exception as exc:
        if "YFRateLimitError" in repr(exc) or "rate limit" in repr(exc).lower():
            print("YFRateLimitError: 요청이 너무 많습니다. 잠시 후 다시 실행하세요.")
            return
        raise

    # 마지막 날 추천 정보 추출
    last_target = result["last_target"]
    rec_data = result["recommendation_data"]
    end_date = rec_data["last_date"]
    offense = settings["trade_ticker"]
    defense = settings["defense_ticker"]
    last_prices = rec_data["last_prices"]
    last_returns = rec_data["last_returns"]
    current_dd = rec_data["current_drawdown"]
    buy_cutoff = rec_data["buy_cutoff"]
    sell_cutoff = rec_data["sell_cutoff"]
    needed_recovery = rec_data["needed_recovery"]

    # 추천 출력 생성
    table_lines = []
    assets = [offense, defense]
    for sym in assets:
        price = last_prices.get(sym, 0.0)
        ret = last_returns.get(sym, 0.0)

        if sym == last_target:
            status = "BUY ✅️"
            note = "타깃"
        elif sym == offense:
            status = "WAIT ⏳️"
            # 공격 자산이 타깃이 아닌 경우: DD 정보 표시
            note = f"DD {current_dd * 100:.2f}% (매수컷 -{buy_cutoff:.2f}%, 필요 {needed_recovery:+.2f}%)"
        else:
            status = "WAIT ⏳️"
            note = "방어"

        table_lines.append(f"📌 {sym}")
        table_lines.append(f"  상태: {status}")
        table_lines.append(f"  일간: {ret * 100:+.2f}%")
        table_lines.append(f"  현재가: ${price:,.2f}")
        if note:
            table_lines.append(f"  비고: {note}")
        table_lines.append("")

    # 로그 파일 저장
    out_dir = Path("zresults")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"recommend_{datetime.now().date()}.log"

    with out_path.open("w", encoding="utf-8") as f:
        f.write(f"추천 로그 생성: {datetime.now().isoformat()}\n\n")
        f.write("=== 추천 목록 ===\n")
        for line in table_lines:
            f.write(line + "\n")
        f.write("\n")
        f.write(f"[INFO] 기준일: {end_date}\n")
        f.write(f"[INFO] 최종 타깃: {last_target}\n")
        f.write(f"[INFO] 적용 파라미터: {defense} / Buy {buy_cutoff}% / Sell {sell_cutoff}%\n")

    # 콘솔 출력
    print("\n=== 추천 목록 ===")
    for line in table_lines:
        print(line)
    print()
    print(f"[INFO] 기준일: {end_date}")
    print(f"[INFO] 최종 타깃: {last_target}")
    print(f"[INFO] 적용 파라미터: {defense} / Buy {buy_cutoff}% / Sell {sell_cutoff}%")
    print(f"\n추천 결과 저장: {out_path}")


if __name__ == "__main__":
    main()
