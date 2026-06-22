# 사용자 가이드 (User Guide) - Index Leverage Switching

## 1. 설치 및 준비
이 프로젝트는 Python 3.10+ 환경에서 동작합니다.

### 필수 패키지 설치
```bash
pip install -r requirements.txt
```
(주요 의존성: `pandas`, `numpy`, `yfinance`)

## 2. 실행 방법

### 워크플로우
권장 실행 순서 (전략 프로파일 인자 `switch` 또는 `buy` 추가, 기본값 `switch`):

```bash
# 1. 튜닝 (최적 파라미터 탐색) → config/{profile}.json 업데이트
python tune.py switch
python tune.py buy
python tune.py switch --slack

# 2. 백테스트 (성과 검증)
python backtest.py switch
python backtest.py buy

# 3. 추천 (오늘의 매매 신호/행동)
python recommend.py switch
python recommend.py buy --slack
```

### 각 스크립트 설명

| 스크립트 | 설명 | 결과 저장 위치 |
|----------|------|----------------|
| `tune.py` | 최적 파라미터 탐색 | `zresults/{profile}/tune_*.log` |
| `backtest.py` | 전략 성과 분석 | `zresults/{profile}/backtest_*.log` |
| `recommend.py` | 오늘의 추천 | `zresults/{profile}/recommend_*.log` |

### Slack 알림 옵션 (`--slack`)
`recommend.py` 실행 시 `--slack` 옵션을 사용하면 설정된 Slack 채널로 추천 결과가 전송됩니다. `tune.py` 실행 시 `--slack` 옵션을 사용하면 튜닝 완료 후 최적 파라미터와 상위 결과가 Slack으로 전송됩니다.
- `.env` 파일에 `SLACK_BOT_TOKEN` 및 `TARGET_CHANNEL_ID`가 설정되어 있어야 합니다.

## 3. 결과 해석

### 추천 출력 예시 (KOR)
```text
=== 추천 목록 ===
📌 122630(KODEX 레버리지)
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

## 4. 설정 파일 (`config/switch.json`, `config/buy.json`)

설정 파일은 `strategy` 필드로 전략을 구분합니다.

### switch (스위칭)
```json
{
    "backtested_date": "2026-06-21",
    "strategy": "switch",
    "market": "kor",
    "months_range": 12,
    "signal": { "ticker": "226490", "name": "KODEX 코스피" },
    "offense": { "ticker": "122630", "name": "KODEX 레버리지" },
    "defense": { "ticker": "CASH", "name": "현금" },
    "drawdown_buy_cutoff": 1.0,
    "drawdown_sell_cutoff": 20.0,
    "slippage": 0.5,
    "benchmarks": [...]
}
```

### buy (무한매수법)
```json
{
    "backtested_date": "2026-06-21",
    "strategy": "buy",
    "market": "kor",
    "months_range": 12,
    "target": { "ticker": "122630", "name": "KODEX 레버리지" },
    "divisions": 40,
    "take_profit_pct": 10.0,
    "slippage": 0.5,
    "benchmarks": [...]
}
```

| 키 | 설명 |
|----|------|
| `strategy` | 전략 구분 (`switch` 또는 `buy`) |
| `market` | 시장 구분 (`kor` 또는 `us`) — 데이터 소스 결정 |
| `months_range` | 백테스트 기간 (개월) |
| `signal`/`offense`/`defense` | (switch) 시그널·공격·방어 자산 객체 |
| `drawdown_buy_cutoff`/`drawdown_sell_cutoff` | (switch) 매수/매도 전환 기준 (%) |
| `target` | (buy) 분할 매수 대상 종목 객체 |
| `divisions` | (buy) 분할 수 (원금을 며칠에 나눠 매수) |
| `take_profit_pct` | (buy) 익절률 (%) — 평단 대비 |

## 5. Oracle VM cron 자동화
실제 추천 배치는 GitHub Actions 가 아닌 Oracle VM 의 호스트 cron 에서 돌아갑니다. 각 추천 배치는 저장된 `config/{profile}.json` 기준으로 `recommend.py {switch|buy}` 만 실행하여 Slack 추천을 전송합니다. 튜닝은 자동 cron 으로 돌리지 않습니다. 로컬에서 `tune.py`를 수동 실행해 `config/*.json`을 갱신한 뒤 커밋/푸시하면 배포 시 서버에 반영됩니다. `upgrade` 브랜치에 푸시하면 `deploy.yml` 이 VM 으로 SSH 배포(`git reset --hard origin/upgrade`)한 뒤 `infra/cron/install.sh` 를 실행하여 crontab 을 자동 반영합니다. 수동 재설치는 VM 에서 `bash ~/apps/leverage-switching/infra/cron/install.sh` 로 가능합니다 (idempotent).

### 튜닝 (수동)
- 로컬에서 `python tune.py switch --slack` / `python tune.py buy --slack` 실행 → `config/*.json` 갱신 → 커밋/푸시로 서버 반영

### 스케줄 (한국 거래일 기준 = 월-금, KST)
switch / buy 두 전략 모두 동일 시각에 실행합니다.
- 09:30 장 시작 30분 후 (장중)
- 15:00 장 마감 30분 전 (장중)
- 15:40 장 마감 10분 후 (장 마감 후)

### VM 에 필요한 환경
- `~/apps/leverage-switching/.env` 에 Slack 토큰/채널 ID 설정 (아래 항목).
- 파이썬 3 및 `python3.12-venv` (Ubuntu 22/24 의 경우 `sudo apt-get install -y python3.12-venv`).

### 필수 환경 변수 (VM 의 `.env`)
- `SLACK_BOT_TOKEN`: Slack API 토큰 (추천/튜닝 결과 Block Kit 알림).
- `TARGET_CHANNEL_ID`: 추천/튜닝 결과를 받을 전용 채널 ID.
- `LOGS_SLACK_WEBHOOK`: 배치 실패 및 배포 결과 알림용 Webhook URL.

### GitHub Secrets (배포용)
- `ORACLE_VM_HOST`, `ORACLE_VM_USERNAME`, `ORACLE_VM_SSH_KEY`: VM SSH 접속 정보.
- `LOGS_SLACK_WEBHOOK`: 배포 성공/실패 Slack 알림 Webhook.
