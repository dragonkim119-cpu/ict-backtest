# ICT Backtest Dashboard — 사용자 매뉴얼

> **대상**: ICT/SMC 기반 비트코인 트레이더  
> **프로그램**: 개인용 패턴 분석 + 백테스트 + 매매 일지 + 거시경제 대시보드

---

## 목차

1. [프로그램 개요](#1-프로그램-개요)
2. [시작하기 (설치 및 실행)](#2-시작하기)
3. [차트 탭](#3-차트-탭)
   - 기본 조작
   - ICT 패턴 오버레이
   - 이동평균선 / VWAP
   - 거래량
   - 터틀 트레이딩
4. [백테스트](#4-백테스트)
5. [ICT 7-Step 체크리스트](#5-ict-7-step-체크리스트)
6. [매매 일지](#6-매매-일지)
7. [매크로 대시보드](#7-매크로-대시보드)
8. [텔레그램 알림 설정](#8-텔레그램-알림-설정)
9. [ICT 트레이딩 시나리오](#9-ict-트레이딩-시나리오)
10. [자주 묻는 질문 (FAQ)](#10-faq)

---

## 1. 프로그램 개요

**ICT Backtest Dashboard**는 Binance Futures BTCUSDT(및 기타 USDT 선물 종목)의 과거 데이터를 기반으로:

- **ICT/SMC 패턴**을 자동으로 검출하여 차트에 시각화
- **BPR 진입 룰** 기반 백테스트를 실행하고 성과를 분석
- **매매 일지**를 기록하여 실전 vs 백테스트 성과를 비교
- **거시경제 이벤트**(FOMC, CPI, NFP 등)와 **크립토 뉴스**를 실시간 모니터링
- **텔레그램 알림**으로 진입 기회와 고임팩트 이벤트를 자동 통보

### 기술 스택

| 레이어 | 기술 |
|---|---|
| 백엔드 | Python 3.11+, FastAPI, pandas, pyarrow |
| 프론트엔드 | Next.js 16, TypeScript, Lightweight Charts v5 |
| 데이터 | Parquet (캔들), SQLite (백테스트·일지) |
| 알림 | Telegram Bot API |

---

## 2. 시작하기

### 사전 요구사항

- Python 3.11 이상
- Node.js 18 이상
- pnpm (`npm install -g pnpm`)
- uv (`pip install uv`)

### 설치

```bash
# 1. 저장소 클론
git clone https://github.com/dragonkim119-cpu/ict-backtest.git
cd ict-backtest

# 2. Python 가상환경 + 의존성
cd backend
uv venv
uv pip install -r requirements.txt

# 3. 프론트엔드 의존성
cd ../frontend
pnpm install
```

### 환경변수 설정

`backend/.env` 파일 생성 (`.env.example` 참고):

```env
DATA_DIR=./data

# 텔레그램 알림 (선택)
TELEGRAM_BOT_TOKEN=123456789:AAABBBCCC...
TELEGRAM_CHAT_ID=987654321
TELEGRAM_ALERT_THRESHOLD=5

# 매크로 대시보드 (선택)
FINNHUB_API_KEY=your_key   # finnhub.io 무료 가입
```

> **Finnhub API 키 발급**: [finnhub.io](https://finnhub.io) → 회원가입 → Dashboard → API Key (무료, 카드 불필요)

### 실행

```bash
# Windows: 루트 폴더에서
start.bat

# 수동 실행
# 터미널 1 (백엔드)
cd backend
.venv/Scripts/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 터미널 2 (프론트엔드)
cd frontend
pnpm dev --port 3001
```

브라우저에서 `http://localhost:3001` 접속

---

## 3. 차트 탭

### 기본 조작

| 동작 | 방법 |
|---|---|
| 종목 변경 | 좌상단 입력창에 심볼 입력 후 Enter (예: `ETHUSDT`) |
| 타임프레임 변경 | 드롭다운 선택 (1m / 5m / 15m / 1h / 4h / 1d) |
| 날짜 범위 설정 | 시작일 ~ 종료일 입력 후 **Load Chart** |
| 데이터 수집 | **Ingest Data** 클릭 (최근 365일 수집) |
| Y축 자동 조정 | 차트 우하단 **A** 버튼 |
| 패턴 표시/숨김 | 상단 토글 버튼 클릭 |

### OHLC 툴팁

차트 위에 마우스를 올리면 좌상단에 표시:
```
O 95,200.1  H 95,800.3  L 94,900.2  C 95,500.0
MA20 95,200  MA50 94,800  EMA50 94,750  VWAP 95,100
```

---

### ICT 패턴 오버레이

#### FVG (Fair Value Gap)
- **초록 박스**: 불리쉬 FVG — 상승 임펄스 이후 가격이 채우지 못한 공백
- **빨강 박스**: 베어리쉬 FVG — 하락 임펄스 이후 공백
- **미티게이션**: 가격이 FVG를 재방문하면 박스가 닫힘
- **활용**: FVG는 기관이 미처 체결하지 못한 주문이 남아있는 구간. 가격 재방문 시 되튕길 가능성 높음

#### IFVG (Inversion Fair Value Gap)
- FVG가 완전히 미티게이션된 후 반전된 구간
- 기존 지지→저항, 기존 저항→지지로 역할 전환

#### BPR (Balanced Price Range)
- **밝은 박스 (두꺼운 테두리)**: 두 개의 FVG가 겹치는 구간
- 불리쉬 BPR: 상승 FVG와 하락 FVG의 교집합 → 강한 지지
- 베어리쉬 BPR: 반대 방향 → 강한 저항
- **활용**: 백테스트 진입 룰의 핵심 구간. BPR 터치 시 진입 신호

#### Liquidity Pool (유동성 풀)
- **빨강 수평선**: BSL (Buy Side Liquidity) — 고점 위 매수 스탑 집결
- **초록 수평선**: SSL (Sell Side Liquidity) — 저점 아래 매도 스탑 집결
- `✓` 표시: 이미 스윕(sweep)된 유동성

#### Sweep (유동성 사냥)
- **빨강 화살표(↓)**: Bear Sweep — BSL 위로 급등 후 반락. 롱 스탑 청산 유발
- **초록 화살표(↑)**: Bull Sweep — SSL 아래로 급락 후 반등. 숏 스탑 청산 유발
- **활용**: Sweep 직후 방향 전환 확인 → 역방향 진입 기회

#### Kill Zone (킬 존)
- **반투명 배경**: 기관 활동이 집중되는 시간대 (KST 기준)

| 세션 | KST 시간 | 특징 |
|---|---|---|
| Asia | 00:00 ~ 04:00 | 유동성 형성, 범위 설정 |
| London | 09:00 ~ 12:00 | 주요 방향성 결정 |
| NY AM | 22:00 ~ 01:00 | 가장 높은 거래량 |
| NY PM | 02:00 ~ 04:00 | 세션 마무리 |

#### PO3 / AMD (Power of 3 / Accumulation-Manipulation-Distribution)
- **회색 박스**: 누적(Accumulation) — 기관이 포지션 축적하는 횡보 구간
- **초록/빨강 박스**: 분배(Distribution) — 추세 방향 이동
- **주황 마커 (M)**: 조작(Manipulation) — 페이크 무브, 반대방향 스탑 청산
  - `M(L)`: London 세션 조작
  - `M(N)`: NY 세션 조작

---

### 이동평균선 / VWAP

| 지표 | 색상 | 용도 |
|---|---|---|
| MA 20 | 주황 실선 | 단기 추세, 가격 되돌림 기준 |
| MA 50 | 파랑 실선 | 중기 추세, ICT 변위 확인 |
| MA 200 | 빨강 굵은 실선 | 장기 트렌드 필터 |
| EMA 50 | 보라 점선 | 지수 가중, 최근 데이터 반응 빠름 |
| VWAP | 흰색 실선 | 기관 참조 레벨, 일별 리셋 (UTC) |

#### MA 이격률 패널

차트 위에 표시:
```
MA20 +1.23%   MA50 -0.45%   MA200 +5.67%   VWAP -0.31%
```
- **양수(초록)**: 현재가가 해당 지표 위 → Premium 구간
- **음수(빨강)**: 현재가가 해당 지표 아래 → Discount 구간

#### MA 크로스오버 마커

| 마커 | 의미 |
|---|---|
| 주황 원 `20×50↑` | MA20이 MA50 위로 돌파 (단기 강세) |
| 파랑 원 `20×50↓` | MA20이 MA50 아래로 이탈 (단기 약세) |
| 황금 화살표 `GX` | MA50이 MA200 위로 돌파 — 골든크로스 |
| 빨강 화살표 `DX` | MA50이 MA200 아래로 이탈 — 데스크로스 |

#### VWAP 활용법

- 현재가 > VWAP: 불리쉬 바이어스 → 롱 우선
- 현재가 < VWAP: 베어리쉬 바이어스 → 숏 우선
- VWAP 아래 BPR 터치 = Discount 구간 + 기관 참조 레벨 → 강한 롱 진입 후보

---

### 거래량

- 차트 하단 20%에 히스토그램으로 표시
- **초록**: 상승 캔들, **빨강**: 하락 캔들
- 패턴 + 거래량 급증 조합 → 기관 참여 확인

---

### 터틀 트레이딩 (Donchian Channel)

| 채널 | 색상 | 진입 | 청산 |
|---|---|---|---|
| Turtle S1 | 초록 | 20일 신고점 돌파 | 10일 신저점 이탈 |
| Turtle S2 | 파랑 | 55일 신고점 돌파 | 20일 신저점 이탈 |

**신호 마커**:
- `S1▲` / `S2▲`: 시스템 1/2 롱 진입
- `S1▼` / `S2▼`: 시스템 1/2 숏 진입
- `S1×` / `S2×`: 청산

---

## 4. 백테스트

### 실행 방법

1. **날짜 범위** 설정 (시작일 ~ 종료일)
2. **옵션 설정**:
   - `KZ Only`: 킬 존 시간대 진입만 허용
   - `Req. Sweep`: 유동성 스윕 이후 진입만 허용
   - `HTF`: 상위 타임프레임 BPR 필터 (예: 1h 차트에서 4h BPR 필터)
3. **Run Backtest** 클릭

### 결과 해석

| 지표 | 의미 | 목표 |
|---|---|---|
| Win Rate | 승률 | > 40% |
| Profit Factor | 총수익 / 총손실 | > 1.5 |
| Expectancy | 평균 기댓값 (R) | > 0 |
| Total PnL (R) | 총 손익 (리스크 배수) | 양수 |
| Max Drawdown | 최대 낙폭 (R) | < 10R |
| Avg Duration | 평균 보유 캔들 수 | — |

### 백테스트 히스토리

- **History** 버튼으로 이전 결과 조회
- 두 개의 run을 선택 후 **Compare** → 파라미터별 성과 비교
- `KZ Only + Req. Sweep` 조합이 일반적으로 승률 높음

---

## 5. ICT 7-Step 체크리스트

**Checklist** 버튼으로 현재 시장 상태를 7가지 기준으로 자동 평가:

| # | 항목 | 내용 |
|---|---|---|
| 1 | HTF Trend | HTF BPR 기준 상위 트렌드 확인 |
| 2 | Kill Zone | 현재 킬 존 시간대 여부 |
| 3 | Liquidity Swept | 최근 유동성 스윕 발생 여부 |
| 4 | BPR Present | 유효한 BPR 존재 여부 |
| 5 | Price in BPR | 현재가 BPR 내부 위치 여부 |
| 6 | FVG Confluence | BPR과 FVG 겹침 (컨플루언스) 여부 |
| 7 | SL Acceptable | 손절 가격이 허용 범위 내 (< 3%) 여부 |

- **Score 5/7 이상**: 진입 조건 양호
- `TELEGRAM_ALERT_THRESHOLD=5` 설정 시 점수 초과 자동 텔레그램 발송
- 라이브 모드에서 캔들 마감마다 자동 업데이트

---

## 6. 매매 일지

Journal 탭에서 실제 매매를 기록하고 통계 분석.

### 일지 작성

| 필드 | 설명 |
|---|---|
| Symbol / Interval | 종목 및 타임프레임 |
| Direction | Long / Short |
| Entry / Exit Time | 진입·청산 시간 |
| Entry / Exit Price | 진입·청산 가격 |
| SL / TP | 손절·익절 가격 |
| Result PnL | 손익 (R 배수로 입력 추천) |
| Notes | 진입 근거, 실수 기록 |
| Tags | 분류 태그 (예: `bpr`, `sweep`, `kz`) |
| Linked Run | 백테스트 run ID 연결 |

### 통계 대시보드

- **승률/PnL**: 요일별, 시간대별, 월별 분포
- **방향별**: 롱 vs 숏 성과 비교
- **실전 vs 백테스트**: 두 시스템의 승률·PF·기댓값 비교

### 백테스트 비교

일지 상세에서 **연결된 백테스트 run** 불러오기 → 실전 진입가 vs 백테스트 진입가 비교

---

## 7. 매크로 대시보드

Macro 탭에서 비트코인 가격에 영향을 주는 거시경제 이벤트 모니터링.

### 경제지표 캘린더

| 임팩트 | 주요 지표 | 비트코인 영향 |
|---|---|---|
| 🔴 High | NFP(고용), FOMC 금리결정, CPI, ISM PMI | 변동성 급증 |
| 🟡 Medium | ADP 고용, PPI, 소비자신뢰지수, 연준 위원 발언 | 중간 영향 |
| ⚪ Low | 주간 실업수당, 소규모 경제지표 | 제한적 |

- **시간 표시**: KST 기준 자동 변환
- **예상치 vs 실제**: 실제 발표 후 자동 업데이트
- 고임팩트 이벤트 2시간 전 텔레그램 알림 자동 발송

### 뉴스 피드

- **크립토 탭**: CoinDesk + Cointelegraph RSS + Finnhub 크립토 뉴스
- **거시경제 탭**: 트럼프 발언, 연준 관련, 관세, 전쟁/지정학 필터링 뉴스

### 설정

| 설정 | 옵션 |
|---|---|
| 경제지표 조회 범위 | 3 / 7 / 14 / 30일 |
| 자동 갱신 간격 | 1 / 5 / 15 / 30 / 60분 |

---

## 8. 텔레그램 알림 설정

### 봇 생성

1. 텔레그램에서 `@BotFather` 검색
2. `/newbot` 명령 → 봇 이름 입력 → **TOKEN** 발급
3. 생성한 봇과 대화 시작 (아무 메시지 전송)
4. `https://api.telegram.org/bot{TOKEN}/getUpdates` 접속 → `chat_id` 확인

### .env 설정

```env
TELEGRAM_BOT_TOKEN=123456789:AAABBBCCC...
TELEGRAM_CHAT_ID=987654321
TELEGRAM_ALERT_THRESHOLD=5   # 체크리스트 점수 임계값
```

### 알림 종류

| 알림 | 트리거 조건 |
|---|---|
| ICT 진입 신호 | 체크리스트 Score ≥ Threshold (라이브 캔들 마감 시) |
| 고임팩트 이벤트 | FOMC·NFP·CPI 등 2시간 전 |

---

## 9. ICT 트레이딩 시나리오

### 시나리오 1 — BPR 롱 진입 (기본 셋업)

**조건**: 상승 트렌드 + London Kill Zone + SSL Sweep 후 BPR 터치

```
1. [HTF 확인] 4h 차트에서 HTF BPR이 가격 아래 위치 → 상승 바이어스
2. [KZ 진입] London Kill Zone (KST 09:00~12:00) 진입
3. [Sweep] SSL(저점 아래 유동성) 스윕 마커 확인 (초록 화살표↑)
4. [BPR 터치] 가격이 불리쉬 BPR 구간 진입
5. [추가 확인]
   - VWAP 아래 위치 (Discount 구간)
   - MA200 이격률 음수 (Discount)
   - 체크리스트 Score ≥ 5
6. [진입] BPR 하단 근처 롱, SL = BPR 아래, TP = 최근 BSL(고점 위 유동성)
```

**기대 R:R = 2:1 이상**

---

### 시나리오 2 — PO3 셋업 (AMD 패턴)

**조건**: NY AM Kill Zone + 조작 캔들(M) 확인

```
1. [누적 확인] 회색 박스(Accumulation) 내 횡보 구간 식별
2. [조작 감지] 주황 M 마커 — 조작 방향 반대로 이동 (페이크 무브)
   예: 불리쉬 PO3 → 일시 하락 (SSL Sweep) 후 급등
3. [진입] 조작 캔들 종가 또는 직후 캔들 시가
4. [목표] 분배(Distribution) 박스 상단
```

---

### 시나리오 3 — 거시경제 이벤트 대응

**조건**: FOMC 금리 발표 전후

```
[발표 전]
- Macro 탭 → 경제지표 캘린더에서 FOMC 시간 확인
- 텔레그램 알림으로 2시간 전 사전 경고 수신
- 발표 30분 전 포지션 축소 or 관망

[발표 후]
- 뉴스 탭에서 "Federal Reserve", "interest rate" 기사 확인
- 시장 반응 방향 확인 후 BPR 되돌림 기다림
- 체크리스트 재실행 → Score 확인 후 진입
```

---

### 시나리오 4 — 터틀 트레이딩 (추세 추종)

**조건**: 강한 추세장, ICT 패턴이 불명확한 경우

```
1. Turtle S2 토글 ON → 55일 도나치안 채널 확인
2. S2▲ 진입 신호 마커 발생 (55일 신고점 돌파)
3. SL = 20일 신저점 (S2× 청산 신호)
4. 추세 지속 시 S1 신호(20일)로 피라미딩 가능
```

> **주의**: 터틀 전략은 횡보장에서 잦은 손절 발생. 강한 추세가 확인된 후 사용.

---

### 시나리오 5 — MA 골든크로스 + ICT 컨플루언스

**조건**: MA50이 MA200 위로 골든크로스 + BPR 되돌림

```
1. 골든크로스 마커(GX 황금 화살표) 확인
2. 이후 첫 번째 BPR 되돌림 구간 대기
3. MA200 이격률 패널에서 +5% 이하 (과매수 아님) 확인
4. BPR + VWAP Discount + Kill Zone 3중 컨플루언스 진입
```

---

## 10. FAQ

**Q: 데이터가 없다고 나와요**  
A: **Ingest Data** 버튼 클릭 → 최근 365일 데이터 수집. 최초 실행 시 수 분 소요.

**Q: 백테스트 결과가 없어요**  
A: 날짜 범위 내 BPR 조건을 만족하는 캔들이 없는 경우. 날짜 범위 확장 또는 옵션(`KZ Only`, `Req. Sweep`) 해제 후 재시도.

**Q: 경제지표 캘린더가 비어있어요**  
A: `FINNHUB_API_KEY`가 `.env`에 설정되어 있는지 확인. Macro 탭 우상단 `Finnhub ✓/✗` 뱃지로 상태 확인.

**Q: VWAP이 1d 봉에서 이상해요**  
A: 1일봉에서 VWAP = 당일 typical price와 거의 동일. 의미있는 VWAP은 **1h 이하** 타임프레임에서 사용 권장.

**Q: MA 크로스 마커가 안 보여요**  
A: 두 MA 모두 토글 ON 상태여야 마커 표시. MA20+MA50 둘 다 ON → 20×50 크로스 표시.

**Q: 실시간 모드에서 패턴이 업데이트 안 돼요**  
A: Live 버튼 ON 상태인지 확인. WS 연결 상태가 `● LIVE`(초록)인지 확인. 패턴은 캔들 **마감** 시에만 업데이트됨.

**Q: 멀티 심볼 지원 종목은?**  
A: Binance Futures USDT 마진 종목 전체 가능. `ETHUSDT`, `SOLUSDT`, `BNBUSDT` 등 입력 후 Ingest → Load Chart.

---

*최종 업데이트: 2026-05-30*
