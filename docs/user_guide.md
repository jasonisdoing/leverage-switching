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
권장 실행 순서:

```bash
# 1. 튜닝 (최적 파라미터 탐색) → settings.json 업데이트
python tune.py

# 2. 백테스트 (성과 검증)
python backtest.py

# 3. 추천 (오늘의 매매 신호)
python recommend.py
```

### 각 스크립트 설명

| 스크립트 | 설명 | 결과 저장 위치 |
|----------|------|----------------|
| `tune.py` | 최적 파라미터 탐색 (약 10초) | `zresults/tune_*.log` |
| `backtest.py` | 전략 성과 분석 | `zresults/backtest_*.log` |
| `recommend.py` | 오늘의 추천 | `zresults/recommend_*.log` |

## 3. 결과 해석

### 추천 출력 예시
```text
=== 추천 목록 ===
📌 TQQQ
  상태: WAIT ⏳️
  일간: +1.03%
  현재가: $53.52
  비고: DD -2.94% (매수컷 -0.30%, 필요 +2.64%)

📌 GDX
  상태: BUY ✅️
  일간: +0.29%
  현재가: $87.79
  비고: 타깃


[INFO] 기준일: 2025-12-19
[INFO] 최종 타깃: GDX
[INFO] 적용 파라미터: GDX / Buy 0.3% / Sell 0.4%
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

## 4. 설정 파일 (`settings.json`)

```json
{
    "months_range": 12,
    "signal_ticker": "QQQ",
    "trade_ticker": "TQQQ",
    "defense_ticker": "GDX",
    "drawdown_buy_cutoff": 0.3,
    "drawdown_sell_cutoff": 0.4,
    "slippage": 0.05,
    "benchmarks": [...]
}
```

| 키 | 설명 |
|----|------|
| `months_range` | 백테스트 기간 (개월) |
| `signal_ticker` | 시그널 참조 종목 (QQQ) |
| `trade_ticker` | 공격 자산 (TQQQ) |
| `defense_ticker` | 방어 자산 (GDX, GLDM 등) |
| `drawdown_buy_cutoff` | 매수 전환 기준 (%) |
| `drawdown_sell_cutoff` | 매도 전환 기준 (%) |
