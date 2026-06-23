# Leverage Strategies (Switch / Buy)

## 1. 전략 개요 (Strategy)
한국 레버리지 ETF(KODEX 레버리지 등)를 대상으로 두 가지 전략을 운용합니다.

### 🔁 switch — 2-Tier Hysteresis Switching (스위칭)
**기초 지수(KODEX 코스피)의 고점 대비 하락률**을 기준으로 공격 자산과 방어 자산을 동적으로 교체합니다.
매수/매도 임계값을 분리(이중 임계값)해 횡보장의 잦은 매매(Whipsaw)를 줄입니다.

| 구분 | 내용 | 비고 |
| :--- | :--- | :--- |
| **시그널 자산** | 226490 (KODEX 코스피) | 추세 판단 기준 |
| **공격 자산** | 122630 (KODEX 레버리지) | 강세장 수익 |
| **방어 자산** | 현금(CASH) 등 | 약세장 방어 |
| **매수/매도 임계값** | `config/switch.json` | 튜닝으로 갱신 |

### 🛒 buy — 무한매수법 (1단계 단순화 버전)
단일 대상 종목을 **현금에서 매일 1/N씩 분할 매수**하고, 보유 전량이 **평단 +익절률**에 도달하면 전량 익절하고 다음 거래일부터 새 사이클을 반복합니다. 분할 소진 시 추가 매수 없이 보유(존버)합니다.

| 구분 | 내용 | 비고 |
| :--- | :--- | :--- |
| **대상 종목** | 122630 (KODEX 레버리지) | `config/buy.json` |
| **분할 수 / 익절률** | 예: 40분할 / +10% | 튜닝으로 갱신 |
| **체결 가정** | 시초가 매수·익절 (일봉 기반) | 1단계 단순화 |

> 무한매수법은 강한 상승장에서 +익절률마다 현금화하므로 단순보유 대비 업사이드를 일부 포기하는 특성이 있습니다.

---

## 2. 주요 기능
- **전략 프로파일**: `switch`(스위칭) / `buy`(무한매수법) 두 전략을 동일한 명령 구조로 운용.
- **파라미터 튜닝**: `tune.py`로 과거 데이터 기반 최적 파라미터를 전수 탐색하고 `config/*.json`에 반영.
- **성과 검증**: `backtest.py`로 CAGR, MDD 등 과거 성과를 분석.
- **매매 추천**: `recommend.py`로 오늘의 포지션/행동을 결정.
- **Slack 연동**: 추천 및 튜닝 결과를 Slack으로 전송.
- **Oracle VM cron 자동화**: 한국 거래일에 두 전략의 추천을 하루 3회 자동 실행.

## 3. 상세 문서
- 📘 [시스템 아키텍처](docs/system_architecture.md): 프로젝트 구조 및 데이터 흐름
- 🧠 [전략 로직 상세](docs/strategy_logic.md): 알고리즘 및 튜닝 프로세스
- 📖 [사용자 가이드](docs/user_guide.md): 실행 방법 및 결과 해석

## 4. 실행
모든 스크립트는 전략 프로파일 인자(`switch` 또는 `buy`)를 받습니다. (기본값: `switch`)
시장(market)은 `config/{profile}.json`의 `market` 필드로 결정됩니다.

```bash
# 1. 튜닝 (최적 파라미터 탐색 → config 갱신)
python tune.py switch
python tune.py buy
python tune.py switch --slack   # 튜닝 후 Slack 전송

# 2. 백테스트 (성과 검증)
python backtest.py switch
python backtest.py buy

# 3. 추천 (매매 신호 생성)
python recommend.py switch
python recommend.py buy --slack  # 실행 후 Slack 전송
```

## 5. 자동화 (Automation)
이 프로젝트는 Oracle VM 의 호스트 cron 을 통해 한국 거래일(월-금)에 `switch`/`buy` 두 전략의 추천을 하루 4회 자동 실행합니다. 튜닝은 자동 실행하지 않고, 로컬에서 `tune.py`를 수동 실행해 `config/*.json`을 갱신한 뒤 커밋/푸시하면 배포로 서버에 반영됩니다. `upgrade` 브랜치에 푸시하면 GitHub Actions(`deploy.yml`)가 VM 으로 SSH 배포(`git reset --hard`)하고, 배포 말미에 `infra/cron/install.sh` 를 돌려 crontab 까지 자동 반영합니다.

- **🇰🇷 한국 시장 (KST, DST 없음)** — switch / buy 동일 스케줄
    - **09:30**: 장 시작 30분 후 (장중)
    - **12:00**: 정각 (장중)
    - **15:00**: 장 마감 30분 전 (장중)
    - **15:40**: 장 마감 10분 후 (장 마감 후)

cron 정의는 `infra/cron/crontab`, 설치 스크립트는 `infra/cron/install.sh` 에 있습니다. install.sh 는 마커 기반 idempotent 라 같은 VM 에서 돌아가는 다른 앱의 crontab 을 보존합니다.

## ⚠️ 면책 조항 (Disclaimer)
이 소프트웨어는 투자를 돕기 위한 보조 도구입니다. **최종적인 투자 결정과 그에 따른 책임은 전적으로 사용자에게 있습니다.** 개발자는 이 프로그램을 사용하여 발생한 금전적 손실에 대해 책임지지 않습니다.
