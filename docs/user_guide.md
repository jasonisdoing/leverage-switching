# 사용자 가이드 (User Guide)

## 1. 설치 및 준비
이 프로젝트는 Python 3.10+ 환경에서 동작합니다.

### 필수 패키지 설치
```bash
pip install -r requirements.txt
```
(주요 의존성: `pandas`, `numpy`, `yfinance`)

## 2. 실행 방법

### 워크플로우
권장 실행 순서 (시장 인자 `us` 또는 `kor` 추가):

```bash
# 1. 튜닝 (최적 파라미터 탐색) → config/ 마켓별 파일 업데이트
python tune.py kor

# 2. 백테스트 (성과 검증)
python backtest.py kor

# 3. 추천 (오늘의 매매 신호)
python recommend.py kor
```

### 각 스크립트 설명

| 스크립트 | 설명 | 결과 저장 위치 |
|----------|------|----------------|
| `tune.py` | 최적 파라미터 탐색 | `zresults/{market}/tune_*.log` |
| `backtest.py` | 전략 성과 분석 | `zresults/{market}/backtest_*.log` |
| `recommend.py` | 오늘의 추천 | `zresults/{market}/recommend_*.log` |

## 3. 결과 해석

### 추천 출력 예시 (KOR)
```text
=== 추천 목록 ===
📌 418660(TIGER 미국나스닥100레버리지)
  상태: WAIT ⏳️
  일간: +1.03%
  현재가: 35,350원
  비고: DD -2.94% (매수컷 -0.30%, 필요 +2.64%)

📌 161510(PLUS 고배당주)
  상태: BUY ✅️
  일간: +0.29%
  현재가: 21,245원
  비고: 타깃


[INFO] 기준일: 2025-12-19
[INFO] 최종 타깃: 161510(PLUS 고배당주)
[INFO] 적용 파라미터: 161510(PLUS 고배당주) / Buy 1.5% / Sell 2.7%
```

### 출력 항목 설명

| 항목 | 설명 |
|------|------|
| **상태** | `BUY ✅️` = 매수 대상, `WAIT ⏳️` = 대기 |
| **일간** | 전일 대비 수익률 |
| **현재가** | 최근 종가 |
| **비고** | 타깃 여부 또는 매수 조건 설명 |

### 비고(DD) 해석
```
DD -2.94% (매수컷 -0.30%, 필요 +2.64%)
```
- 현재 QQQ의 고점 대비 하락률: **-2.94%**
- 매수 전환 기준: **-0.30%** (이보다 회복되면 매수)
- 필요 회복폭: **+2.64%** (아직 2.64% 더 올라야 매수 조건 충족)

## 4. 설정 파일 (`config/us.json`, `config/kor.json`)

```json
{
    "backtested_date": "2025-12-20",
    "market": "us",
    "months_range": 12,
    "signal": {
        "ticker": "QQQ",
        "name": "Nasdaq 100 ETF"
    },
    "offense": {
        "ticker": "TQQQ",
        "name": "Nasdaq 3배 레버리지"
    },
    "defense": {
        "ticker": "GDX",
        "name": "반에크 금광 ETF"
    },
    "drawdown_buy_cutoff": 0.3,
    "drawdown_sell_cutoff": 0.4,
    "slippage": 0.05,
    "benchmarks": [...]
}
```

| 키 | 설명 |
|----|------|
| `backtested_date` | 마지막으로 튜닝/백테스트된 날짜 |
| `market` | 시장 구분 (`us` 또는 `kor`) |
| `months_range` | 백테스트 기간 (개월) |
| `signal` | 시그널 참조 종목 객체 (ticker, name) |
| `offense` | 공격 자산 객체 (ticker, name) |
| `defense` | 방어 자산 객체 (ticker, name) |
| `drawdown_buy_cutoff` | 매수 전환 기준 (%) |
| `drawdown_sell_cutoff` | 매도 전환 기준 (%) |
