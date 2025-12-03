# 시스템 아키텍처 (System Architecture)

## 1. 프로젝트 개요
이 프로젝트는 **나스닥 레버리지 스위칭 전략**을 자동으로 최적화하고 매매 추천을 생성하는 시스템입니다. 핵심은 과거 데이터를 기반으로 최적의 파라미터를 찾는 **튜닝(Tuning)** 과정과, 이를 바탕으로 현재 시점의 포지션을 결정하는 **추천(Recommendation)** 과정의 통합입니다.

## 2. 파일 구조 및 역할

### 핵심 실행 파일
- **`nasdaq_switching.py`**: **[메인]** 독립형 실행 스크립트.
    - **역할**: 전체 튜닝 로직과 추천 로직을 모두 포함하고 있어, 이 파일 하나만으로 시스템 구동이 가능합니다.
    - **기능**:
        1. **자동 튜닝**: `TUNING_CONFIG`에 정의된 범위 내에서 전수 조사(Exhaustive Search)를 수행.
        2. **추천 생성**: 튜닝된 최적 파라미터를 적용하여 현재 포지션(BUY/WAIT) 결정.
        3. **API 제공**: `get_result()` 함수를 통해 외부 스크립트에서 결과를 호출 가능.
    - **특징**: `settings.json` 등의 외부 파일 의존성이 없습니다.

### 개발 및 실험용 스크립트
- **`tune.py`**: 튜닝 로직 개발 및 테스트용 스크립트.
- **`recommend.py`**: 추천 로직 개발 및 테스트용 스크립트.
- **`logic/`**: 비즈니스 로직이 모듈화된 패키지.
    - `logic/backtest/`: 백테스팅 엔진 (`runner.py`).
    - `logic/tune/`: 튜닝 실행 로직 (`runner.py`).
    - `logic/common/`: 공통 유틸리티 및 시그널 계산 (`signals.py`, `settings.py`).

### 설정 및 데이터
- **`settings.json`**: (선택 사항) 사용자가 수동으로 설정을 오버라이드하고 싶을 때 사용. `nasdaq_switching.py`는 이 파일이 없어도 내부 기본값으로 동작합니다.
- **`zresults/`**: 백테스트 및 튜닝 로그가 저장되는 디렉토리.
- **`znotes/`**: 사용자 메모 및 노트.

## 3. 데이터 흐름 (Data Flow)

1. **초기화**: `nasdaq_switching.py` 실행 시 내부 기본 설정(`DEFAULT_SETTINGS`) 로드.
2. **데이터 수집**: `yfinance`를 통해 `QQQ`(시그널), `TQQQ`(공격), `GLDM`(방어) 등의 과거 주가 데이터 다운로드.
3. **튜닝 (Optimization)**:
    - `TUNING_CONFIG`에 정의된 수천 개의 파라미터 조합 생성.
    - 병렬 처리(`ProcessPoolExecutor`)를 통해 각 조합에 대한 백테스트 수행.
    - **CAGR(연평균 수익률)**이 가장 높은 파라미터 세트 선정.
4. **추천 (Recommendation)**:
    - 선정된 최적 파라미터(`buy_cutoff`, `sell_cutoff`, `defense_ticker`) 적용.
    - 최신 데이터를 바탕으로 현재 상태(`drawdown`) 계산 및 포지션 결정.
5. **출력**:
    - 콘솔에 튜닝 결과 및 추천 테이블 출력.
    - `get_result()` 호출 시 딕셔너리 형태로 결과 반환.
