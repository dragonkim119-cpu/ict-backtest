# CLAUDE.md — ICT Backtest 프로젝트 컨텍스트

이 문서는 Claude Code가 프로젝트 진입 시 자동으로 참조하는 핵심 컨텍스트 파일입니다.
**작업 전 반드시 이 파일과 `docs/` 디렉토리의 모든 문서를 읽으세요.**

---

## 프로젝트 한 줄 요약

**개인용 ICT/SMC + 터틀 트레이딩 웹 대시보드** — Binance Futures BTCUSDT 과거 데이터에서 ICT 패턴(FVG, BPR, Sweep 등)과 터틀 트레이딩(도나치안 채널)을 차트에 표시하고, BPR 진입 룰 백테스트 + 매매 일지 + 텔레그램 알림을 제공합니다.

---

## 현재 단계 및 브랜치

| 브랜치 | 내용 | 상태 |
|---|---|---|
| `main` | Phase 1~3 전체 완료 (안정) | ✅ |
| `feature/turtle-trading` | 터틀 도나치안 채널 오버레이 추가 | ✅ 진행 중 |
| `v3.0-stable` (태그) | Phase 3 완료 시점 체크포인트 | — |

**현재 작업 브랜치**: `feature/turtle-trading`

---

## Phase별 완료 현황

### Phase 1 — 백테스팅 코어

| Week | 내용 | 상태 |
|---|---|---|
| 1 | 프로젝트 셋업, Binance kline 수집, Parquet I/O | ✅ |
| 2 | FVG / IFVG / Swing High-Low 검출 | ✅ |
| 3 | Liquidity Pool / Sweep / BPR / Kill Zone 검출 | ✅ |
| 4 | FastAPI 엔드포인트 + Next.js 차트 + 패턴 오버레이 | ✅ |
| 5 | 백테스트 엔진 (BPR 진입 룰 + SQLite 저장) | ✅ |
| 6 | 백테스트 결과 UI (MetricsPanel + TradesTable) | ✅ |

### Phase 2 — 실시간 분석 + 고급 패턴

| Week | 내용 | 상태 |
|---|---|---|
| 1 | WebSocket 실시간 캔들 스트림 | ✅ |
| 2 | 실시간 패턴 마킹 (closed 캔들마다 재검출) | ✅ |
| 3 | PO3·AMD 패턴 검출 + 차트 오버레이 | ✅ |
| 4 | MTF 백테스트 (HTF BPR 필터) + Run History | ✅ |
| 5 | ICT 7-step 체크리스트 패널 | ✅ |
| 6 | Run 비교 UI (RunHistory + RunComparison) | ✅ |

### Phase 3 — 알림 + 매매 일지

| Week | 내용 | 상태 |
|---|---|---|
| 1 | 텔레그램 봇 알림 (체크리스트 score ≥ threshold 시 자동 발송) | ✅ |
| 2 | 매매 일지 백엔드 (SQLite CRUD + compare 엔드포인트) | ✅ |
| 3 | 매매 일지 UI (JournalForm / Table / Detail) | ✅ |
| 4 | 통계 대시보드 (요일·시간대·월별 승률, 실전 vs 백테스트) | ✅ |

### 터틀 트레이딩 추가 (`feature/turtle-trading`)

| 내용 | 상태 |
|---|---|
| 도나치안 채널 오버레이 (S1: 20/10일, S2: 55/20일) | ✅ |
| 터틀 진입/청산 신호 마커 | ✅ |
| `GET /api/turtle/donchian` 엔드포인트 | ✅ |
| Visibility 토글 (Turtle S1 초록 / Turtle S2 파랑) | ✅ |

---

## 구현 완료 파일 목록

### Backend

**Phase 1**
- `app/data/binance.py` — Binance Futures kline 수집
- `app/data/ingest.py` — 수집 → Parquet upsert
- `app/data/loader.py` — Parquet 로드 (`load_candles`, `get_candle_range`)
- `app/patterns/fvg.py`, `ifvg.py`, `swings.py` — 패턴 검출
- `app/patterns/liquidity.py`, `bpr.py`, `killzone.py`, `atr.py`
- `app/patterns/detect_all.py` — 전체 패턴 파이프라인
- `app/models/candle.py`, `patterns.py`, `trade.py` — Pydantic 스키마
- `app/backtest/entry.py`, `stop.py`, `simulate.py`, `metrics.py`, `engine.py`
- `app/api/candles.py`, `patterns.py`, `ingest.py`, `backtest.py`
- `app/main.py` — FastAPI 앱 + CORS + load_dotenv

**Phase 2 신규**
- `app/api/ws.py` — WebSocket `/ws/kline` + 텔레그램 알림 트리거
- `app/backtest/mtf_entry.py` — MTF BPR 필터
- `app/api/checklist.py` — `GET /api/checklist` + `run_checklist()` 서비스 함수
- `app/patterns/po3.py`, `amd.py` — PO3/AMD 패턴
- `app/backtest/live_detector.py` — 실시간 패턴 재검출

**Phase 3 신규**
- `app/services/telegram.py` — `send_message`, `is_configured`, `get_threshold`
- `app/api/telegram.py` — `GET /api/telegram/status`, `POST /api/telegram/test`
- `app/models/journal.py` — Journal + Stats Pydantic 스키마
- `app/backtest/journal.py` — SQLite CRUD + `get_stats()`, `get_compare_backtest()`
- `app/api/journal.py` — CRUD + `/stats` + `/compare-backtest`

**터틀 트레이딩 신규**
- `app/turtle/indicators.py` — 도나치안 채널 + 신호 계산
- `app/api/turtle.py` — `GET /api/turtle/donchian`

### Frontend

**Phase 1**
- `lib/types.ts`, `lib/api.ts`, `lib/chart-primitives.ts`
- `components/chart/CandleChart.tsx` — 캔들차트 + 패턴 오버레이 + OHLC 툴팁
- `components/backtest/MetricsPanel.tsx`, `TradesTable.tsx`
- `app/page.tsx` — 메인 대시보드

**Phase 2 신규**
- `lib/ws.ts` — `useKlineStream` WebSocket 훅
- `components/backtest/ChecklistPanel.tsx`, `RunHistory.tsx`, `RunComparison.tsx`

**Phase 3 신규**
- `components/journal/JournalForm.tsx`, `JournalTable.tsx`, `JournalDetail.tsx`
- `components/journal/JournalTab.tsx`, `StatsPanel.tsx`, `BacktestCompare.tsx`

**터틀 트레이딩 신규**
- `CandleChart.tsx` — Donchian LineSeries 4개 + 신호 마커
- `lib/types.ts` — `DonchianPoint`, `TurtleSignal`, `TurtleDonchianResponse` 타입

### Tests
- **총 153개 통과** (test_fvg, test_bpr, test_liquidity, test_backtest, test_mtf, test_checklist, test_po3, test_journal × 22개, test_telegram × 10개)

---

## API 엔드포인트 전체 목록

| Method | Path | 기능 |
|---|---|---|
| GET | `/api/candles` | 캔들 조회 |
| GET | `/api/candles/range` | 저장 데이터 범위 조회 |
| GET | `/api/patterns` | 패턴 검출 결과 |
| POST | `/api/ingest` | Binance 데이터 수집 |
| POST | `/api/backtest` | 백테스트 실행 |
| GET | `/api/backtest/runs` | 백테스트 히스토리 |
| GET | `/api/backtest/runs/{run_id}` | 특정 run 상세 |
| GET | `/api/checklist` | ICT 7-step 체크리스트 |
| POST | `/api/journal` | 매매 일지 생성 |
| GET | `/api/journal` | 일지 목록 |
| PUT | `/api/journal/{id}` | 일지 수정 |
| DELETE | `/api/journal/{id}` | 일지 삭제 |
| GET | `/api/journal/{id}/compare` | 백테스트 run 비교 |
| GET | `/api/journal/stats` | 일지 통계 |
| GET | `/api/journal/compare-backtest` | 실전 vs 백테스트 비교 |
| GET | `/api/telegram/status` | 텔레그램 설정 상태 |
| POST | `/api/telegram/test` | 텔레그램 테스트 발송 |
| GET | `/api/turtle/donchian` | 도나치안 채널 + 신호 |
| WS | `/ws/kline` | 실시간 캔들 스트림 |

---

## 주요 기술 결정 사항

### Phase 1
- **lightweight-charts v5**: `chart.addSeries(CandlestickSeries, opts)`
- **Sweep 마커**: `createSeriesMarkers<Time>(series, markers)`
- **DataFrame 비어있음**: `if candles.empty:`
- **SQLite DB**: `DATA_DIR` 환경변수 → `./data/backtest.db`
- **백테스트 필터**: `kill_zone_only` / `require_sweep` → `_params_hash` → 고유 `run_id`
- **CORS**: `localhost:3000` + `localhost:3001`

### Phase 2
- **WebSocket**: `/ws/kline?symbol=BTCUSDT&interval=1h`
- **MTF 필터**: `created_time > entry_time` 가드로 미래 BPR 제외
- **live tick 가드**: `lastSeriesTimeRef` — 시간 역행 시 `update()` 스킵
- **ICT 체크리스트**: `LOOKBACK=500`, `SWEEP_LOOKBACK=20`, `SL_MAX_PCT=0.03`

### Phase 3
- **텔레그램**: `.env`의 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_ALERT_THRESHOLD=5`
- **알림 트리거**: 캔들 close 후 `asyncio.create_task(_check_and_alert)` — non-blocking
- **HTF 자동 매핑**: 1m→5m, 5m→1h, 15m→1h, 1h→4h, 4h→1d
- **일지 DB**: `trade_journal` 테이블을 기존 `backtest.db`에 추가
- **stats 집계 기준**: `result_pnl IS NOT NULL` (closed trades만)

### 차트 관련
- **KST 표시**: `toUTC(iso)` = UTC 타임스탬프 + 9h 오프셋 → 차트 시간축 KST 표시
- **OHLC 툴팁**: `chart.subscribeCrosshairMove()` → 좌상단 O/H/L/C 표시
- **auto-scroll 조건**: `lr.to >= candles.length - 3` 일 때만 `scrollToRealTime()` 호출
- **날짜 자동 세팅**: 마운트 시 `fetchCandleRange()` 호출 → 실제 데이터 범위로 자동 갱신

### 터틀 트레이딩
- **System 1**: 20일 고점 진입 / 10일 저점 청산
- **System 2**: 55일 고점 진입 / 20일 저점 청산
- **채널 계산**: `shift(1)` 기준 — 이전 캔들의 채널로 현재 캔들 신호 판정
- **LineSeries**: `s1Upper/Lower` (초록), `s2Upper/Lower` (파랑) — Donchian ON/OFF 토글

### 운영
- **start.bat**: venv python 명시 + 8000/3001 포트 기존 프로세스 kill 후 기동
- **load_dotenv**: `main.py`에서 `parents[1]/.env` (= `backend/.env`) 로드
- **.gitignore**: `backend/.env` 포함

---

## 기술 스택

| 레이어 | 선택 |
|---|---|
| 백엔드 | Python 3.11+, FastAPI, pandas, numpy, pyarrow, httpx |
| 프론트 | Next.js 16, TypeScript, Tailwind, Lightweight Charts v5 |
| 데이터 | Parquet (캔들), SQLite (백테스트·일지) |
| 알림 | Telegram Bot API (httpx, async) |
| 패키지 매니저 | `uv` (Python), `pnpm` (JS) |

---

## 디렉토리 구조

```
ict-backtest/
├── CLAUDE.md
├── start.bat                  # 서버 기동 (venv + 포트 충돌 방지)
├── docs/
│   ├── 02_PATTERNS.md         # 패턴 알고리즘 (핵심)
│   ├── 03_BACKTEST.md         # BPR 진입 룰
│   └── 05_ROADMAP.md
├── backend/
│   ├── .env                   # TELEGRAM_*, DATA_DIR (gitignore)
│   ├── .env.example
│   ├── app/
│   │   ├── main.py
│   │   ├── api/               # candles, patterns, backtest, checklist,
│   │   │                      # journal, telegram, turtle, ws
│   │   ├── data/              # binance, ingest, loader, ws_binance
│   │   ├── patterns/          # fvg, ifvg, swings, liquidity, bpr,
│   │   │                      # killzone, atr, po3, amd, detect_all
│   │   ├── backtest/          # entry, stop, simulate, metrics, engine,
│   │   │                      # mtf_entry, live_detector, journal
│   │   ├── turtle/            # indicators (도나치안 채널)
│   │   ├── services/          # telegram
│   │   └── models/            # candle, patterns, trade, journal
│   └── tests/                 # 153개 통과
└── frontend/
    ├── app/page.tsx            # Chart / Journal 탭
    ├── components/
    │   ├── chart/CandleChart.tsx   # 차트 + 패턴 + 도나치안 + OHLC 툴팁
    │   ├── backtest/               # MetricsPanel, TradesTable, Checklist,
    │   │                           # RunHistory, RunComparison
    │   └── journal/                # JournalForm, Table, Detail, Tab,
    │                               # StatsPanel, BacktestCompare
    └── lib/
        ├── types.ts            # 모든 TypeScript 타입
        ├── api.ts              # 모든 API 함수
        ├── ws.ts               # useKlineStream 훅
        └── chart-primitives.ts # BoxesPrimitive, KillZonePrimitive, toUTC(KST)
```

---

## 코딩 컨벤션

### Python
- `from __future__ import annotations` 필수
- Pydantic 모델로 스키마 정의
- 패턴 검출 함수는 순수 함수 (DataFrame → 리스트)
- 포매터: `ruff format`, 린터: `ruff check`

### TypeScript
- `strict: true`
- 함수형 컴포넌트 + named export
- 상태관리: React state만 (Redux/Zustand 금지)
- Tailwind 유틸리티 우선

---

## 절대 금지 사항

- ❌ 인증/로그인/멀티 유저
- ❌ 요청하지 않은 추상화 (거래소 base class 등)
- ❌ ICT 외 전략 (RSI, MACD 보조지표)
- ❌ Docker 컨테이너화 (추후 검토)
- ❌ `docs/` 내용과 모순되는 구현 → 작업 멈추고 질문

---

## 작업 흐름

1. 새 모듈 전: `docs/02_PATTERNS.md`, `03_BACKTEST.md` 재확인
2. 패턴 알고리즘: 반드시 `docs/02_PATTERNS.md` 파라미터 그대로 구현
3. BPR 진입 룰: 반드시 `docs/03_BACKTEST.md` 따르기
4. 스키마 변경 시: `docs/04_DATA_MODEL.md` 먼저 갱신
5. 단위 테스트 통과 후 다음 단계 진행

---

## 막혔을 때

- 패턴 정의 모호 → `docs/02_PATTERNS.md` 파라미터 섹션
- 진입/청산 룰 모호 → `docs/03_BACKTEST.md` 트레이드 라이프사이클
- 둘 다 없음 → **임의 결정하지 말고 사용자에게 질문**
