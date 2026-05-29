# CLAUDE.md — ICT Backtest 프로젝트 컨텍스트

이 문서는 Claude Code가 프로젝트 진입 시 자동으로 참조하는 핵심 컨텍스트 파일입니다.
**작업 전 반드시 이 파일과 `docs/` 디렉토리의 모든 문서를 읽으세요.**

---

## 프로젝트 한 줄 요약

**개인용 ICT/SMC 백테스팅 웹 대시보드** — 비트코인 선물(Binance Futures, BTCUSDT) 과거 데이터에서 ICT 패턴(FVG, BPR, Liquidity Sweep 등)을 자동 검출하고 BPR 진입 룰로 백테스트를 수행합니다.

## 현재 단계

**Phase 3 완료** (2026-05-29 기준) — Phase 1 + Phase 2 + Phase 3 전체 구현 완료.

### Phase 1 Week별 완료 현황

| Week | 내용 | 상태 |
|---|---|---|
| 1 | 프로젝트 셋업, Binance kline 수집, Parquet I/O | ✅ 완료 |
| 2 | FVG / IFVG / Swing High-Low 검출 | ✅ 완료 |
| 3 | Liquidity Pool / Sweep / BPR / Kill Zone 검출 | ✅ 완료 |
| 4 | FastAPI 엔드포인트 + Next.js 차트 + 패턴 오버레이 | ✅ 완료 |
| 5 | 백테스트 엔진 (BPR 진입 룰 + SQLite 저장) | ✅ 완료 |
| 6 | 백테스트 결과 UI (MetricsPanel + TradesTable 마무리) | ✅ 완료 |

### Phase 2 Week별 완료 현황

| Week | 내용 | 상태 |
|---|---|---|
| 1 | WebSocket 실시간 캔들 스트림 (Binance WS → FastAPI → 프론트) | ✅ 완료 |
| 2 | 실시간 패턴 마킹 (closed 캔들마다 패턴 재검출 → WS 브로드캐스트) | ✅ 완료 |
| 3 | PO3·AMD 패턴 검출 + 차트 오버레이 | ✅ 완료 |
| 4 | MTF 백테스트 (HTF BPR 필터) + Run History | ✅ 완료 |
| 5 | ICT 7-step 체크리스트 패널 (`GET /api/checklist`) | ✅ 완료 |
| 6 | Run 비교 UI (RunHistory + RunComparison) | ✅ 완료 |

### 구현 완료 파일 목록

**Backend (Phase 1)**
- `app/data/binance.py` — Binance Futures kline 수집
- `app/data/ingest.py` — 수집 → Parquet upsert
- `app/data/loader.py` — Parquet 로드 (`load_candles`, `get_candle_range`, `_to_utc` 헬퍼)
- `app/patterns/fvg.py` — FVG 검출 + 무효화
- `app/patterns/ifvg.py` — IFVG 검출
- `app/patterns/swings.py` — Swing High/Low
- `app/patterns/liquidity.py` — Liquidity Pool + Sweep
- `app/patterns/bpr.py` — BPR (겹치는 FVG 쌍)
- `app/patterns/killzone.py` — Kill Zone 시간대
- `app/patterns/atr.py` — ATR 계산
- `app/patterns/detect_all.py` — 전체 패턴 파이프라인
- `app/models/candle.py`, `app/models/patterns.py` — Pydantic 스키마
- `app/models/trade.py` — `EntrySignal`, `Trade`, `Metrics` 스키마
- `app/backtest/entry.py` — `find_entry_signal`
- `app/backtest/stop.py` — `calc_stop_loss`, `calc_take_profit`
- `app/backtest/simulate.py` — `simulate_trade`
- `app/backtest/metrics.py` — `compute_metrics`
- `app/backtest/engine.py` — `run_backtest` + SQLite 저장 + `list_runs`, `get_run_detail`
- `app/api/candles.py` — `GET /api/candles`, `GET /api/candles/range`
- `app/api/patterns.py` — `GET /api/patterns`
- `app/api/ingest.py` — `POST /api/ingest`
- `app/api/backtest.py` — `POST /api/backtest`, `GET /api/backtest/runs`, `GET /api/backtest/runs/{run_id}`
- `app/main.py` — FastAPI 앱 + CORS

**Backend (Phase 2 신규)**
- `app/api/ws.py` — WebSocket `/ws/kline` (실시간 캔들 + 패턴 브로드캐스트)
- `app/backtest/mtf_entry.py` — `is_within_htf_bpr()` MTF 필터
- `app/api/checklist.py` — `GET /api/checklist` (ICT 7-step 체크리스트)
- `app/patterns/po3.py` — PO3/AMD 패턴 검출

**Frontend (Phase 1)**
- `lib/types.ts` — TypeScript 타입 전체
- `lib/api.ts` — API 함수 전체 (`fetchCandleRange` 포함)
- `lib/chart-primitives.ts` — `BoxesPrimitive`, `KillZonePrimitive`
- `components/chart/CandleChart.tsx` — 캔들차트 + 패턴 오버레이 (HTF BPR 포함)
- `components/backtest/MetricsPanel.tsx`, `TradesTable.tsx`
- `app/page.tsx` — 메인 대시보드

**Frontend (Phase 2 신규)**
- `lib/ws.ts` — `useKlineStream` WebSocket 훅
- `components/backtest/ChecklistPanel.tsx` — ICT 체크리스트 UI
- `components/backtest/RunHistory.tsx` — 백테스트 히스토리 테이블
- `components/backtest/RunComparison.tsx` — Run 비교 UI (사이드-바이-사이드)

**Tests** (121개 전부 통과)
- `tests/test_fvg.py`, `test_ifvg.py`, `test_swings.py`
- `tests/test_liquidity.py` (13개)
- `tests/test_bpr.py` (10개)
- `tests/test_detect_all.py` (8개, 성능 포함)
- `tests/test_backtest.py` (17개)
- `tests/test_mtf.py` (10개) — Phase 2
- `tests/test_checklist.py` (23개) — Phase 2
- `tests/test_po3.py` — Phase 2

### 주요 기술 결정 사항

**Phase 1 확정**
- **lightweight-charts v5 API**: `chart.addSeries(CandlestickSeries, opts)` (v4의 `addCandlestickSeries` 아님)
- **Sweep 마커**: `createSeriesMarkers<Time>(series, markers)` 사용
- **캔버스 드로잉**: `target.useBitmapCoordinateSpace()` → bitmap 좌표 = media 좌표 × pixelRatio
- **DataFrame 비어있음 체크**: `if candles.empty:` (not `if not candles:`)
- **Timezone**: `load_candles`의 `_to_utc()` 헬퍼 — `ts.tzinfo is None`이면 `tz_localize`, 아니면 `tz_convert`
- **SQLite DB 경로**: `DATA_DIR` 환경변수 (기본 `./data/backtest.db`)
- **백테스트 필터**: `kill_zone_only` / `require_sweep` / `_params_hash`에 필터값 포함 → 고유 `run_id`
- **CORS**: `allow_origins`에 `localhost:3000` + `localhost:3001` 모두 등록
- **서버 실행**: `start.bat` 더블클릭으로 백엔드(8000) + 프론트(3001) 동시 기동

**Phase 2 확정**
- **WebSocket 엔드포인트**: `/ws/kline?symbol=BTCUSDT&interval=1h` — `kline` / `patterns` 타입 메시지 전송
- **MTF 필터**: `is_within_htf_bpr(price, entry_time, htf_bprs)` — `created_time > entry_time` 가드로 미래 BPR 제외
- **Run history inf 처리**: `_row_to_dict()`에서 `float('inf')` → `None` 변환 (JSON 직렬화 안전)
- **CandleChart live tick 가드**: `lastSeriesTimeRef` — `newTime < lastSeriesTimeRef` 이면 `update()` 스킵 (interval 전환 시 stale 캔들 방지)
- **interval 변경 시 candles 초기화**: `handleIntervalChange`에서 `setCandles([])` → `isLiveTick = false` 강제
- **ICT 체크리스트 파라미터**: `LOOKBACK=500`, `SWEEP_LOOKBACK=20`, `SL_MAX_PCT=0.03`
- **구간별 Parquet 범위**: 1h (2025-05-26~), 4h (2025-05-27~), 1d (2025-05-28~), 15m (2026-02-26~), 5m (2026-04-27~), 1m (2026-05-20~)
- **`GET /api/candles/range`**: interval 변경 시 프론트가 호출 → 실제 가용 날짜 범위 자동 세팅

**Phase 3 신규 파일 (Week 1 완료)**
- `app/services/telegram.py` — `send_message`, `is_configured`, `get_threshold` (httpx, Bot API)
- `app/api/telegram.py` — `GET /api/telegram/status`, `POST /api/telegram/test`
- `app/api/checklist.py` — `run_checklist()` 서비스 함수 추출 (WS에서 재사용)
- `app/api/ws.py` — 캔들 close 시 checklist 평가 → score ≥ `TELEGRAM_ALERT_THRESHOLD` 이면 텔레그램 알림
- `app/main.py` — `load_dotenv()` 추가 + telegram router 등록

**Phase 3 주요 기술 결정**
- **텔레그램 설정**: `.env`의 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_ALERT_THRESHOLD` (기본 5)
- **알림 트리거**: `_check_and_alert()` — 캔들 close 후 asyncio.create_task로 non-blocking 실행
- **HTF 매핑**: 1m→5m, 5m→1h, 15m→1h, 1h→4h, 4h→1d (ws.py `_HTF` dict)
- **토큰 미설정 시**: `is_configured()` False → graceful skip (서버 크래시 없음)

**Phase 3 Week 2 완료**
- `app/models/journal.py` — `JournalEntryCreate`, `JournalEntryUpdate`, `JournalEntry`, `JournalCompareResult`
- `app/backtest/journal.py` — SQLite CRUD (`trade_journal` 테이블, `backtest.db` 공유)
- `app/api/journal.py` — `POST/GET/PUT/DELETE /api/journal`, `GET /api/journal/{id}/compare`
- `app/main.py` — journal router 등록

**Phase 3 주요 기술 결정 (Week 2)**
- **DB**: `trade_journal` 테이블을 기존 `backtest.db`에 추가 (별도 파일 없음)
- **compare 엔드포인트**: `run_id` 연결 시 `get_run_detail(run_id)` 반환, 미연결 시 null
- **update**: `exclude_none=True` — 명시적으로 전달된 필드만 UPDATE

**Phase 3 Week 3 완료 (프론트)**
- `lib/types.ts` — `JournalEntry`, `JournalEntryCreate`, `JournalEntryUpdate`, `JournalCompareResult`
- `lib/api.ts` — `createJournalEntry`, `fetchJournalEntries`, `fetchJournalEntry`, `updateJournalEntry`, `deleteJournalEntry`, `compareJournalEntry`
- `components/journal/JournalForm.tsx` — 트레이드 기록 폼
- `components/journal/JournalTable.tsx` — 일지 목록 (방향/TF 필터, 삭제)
- `components/journal/JournalDetail.tsx` — 상세 + 편집 + 백테스트 run 비교
- `components/journal/JournalTab.tsx` — 탭 전체 오케스트레이션
- `app/page.tsx` — Chart / Journal 탭 분리

**Phase 3 Week 4 완료 (통계 대시보드)**
- `app/models/journal.py` — stats 모델 6종 추가 (`JournalStats`, `BacktestAggregate`, `JournalVsBacktest` 등)
- `app/backtest/journal.py` — `get_stats()`, `get_compare_backtest()` SQLite 집계 함수
- `app/api/journal.py` — `GET /api/journal/stats`, `GET /api/journal/compare-backtest`
- `components/journal/StatsPanel.tsx` — 요약 카드, 월별 PnL 바차트, 방향·요일·시간대·TF별 승률
- `components/journal/BacktestCompare.tsx` — 실전 vs 백테스트 메트릭 비교 테이블
- `components/journal/JournalTab.tsx` — Entries / Statistics 서브탭 추가

**Phase 3 주요 기술 결정 (Week 4)**
- **stats 집계 기준**: `result_pnl IS NOT NULL` 인 트레이드만 (closed trades)
- **backtest_runs 없을 때**: `OperationalError` graceful skip → `total_runs=0`
- **월별 바차트**: CSS Tailwind, 추가 라이브러리 없음
- **시간대**: entry_time 기준 UTC hour (로컬 타임 변환 없음)

## 핵심 우선순위 (절대 순서)

1. 데이터 파이프라인 (Binance kline 수집 → Parquet 저장)
2. 패턴 검출 엔진 (FVG → IFVG → Swing → Liquidity → Sweep → BPR → Kill Zone 순)
3. 차트 렌더링 + 자동 오버레이
4. 백테스트 엔진 (BPR 진입 룰)
5. 백테스트 결과 리포트 UI

## 기술 스택 (확정)

| 레이어 | 선택 |
|---|---|
| 백엔드 | Python 3.11+, FastAPI, pandas, numpy, pyarrow |
| 프론트 | Next.js 14+ (App Router), TypeScript, Tailwind, shadcn/ui |
| 차트 | TradingView Lightweight Charts (v4+) |
| 데이터 저장 | Parquet (캔들), SQLite (백테스트 결과/일지) |
| 데이터 소스 | Binance Futures REST API (`/fapi/v1/klines`) |
| 패키지 매니저 | `uv` (Python), `pnpm` (JS) |

## 디렉토리 구조 (기대값)

```
ict-backtest/
├── CLAUDE.md                # 이 파일
├── README.md
├── docs/                    # 스펙 문서 (작업 시 반드시 참조)
│   ├── 01_SPEC.md
│   ├── 02_PATTERNS.md       # 패턴 검출 알고리즘 (핵심)
│   ├── 03_BACKTEST.md       # BPR 진입 룰
│   ├── 04_DATA_MODEL.md
│   └── 05_ROADMAP.md
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py          # FastAPI 엔트리
│   │   ├── api/             # 라우터
│   │   ├── data/            # Binance 수집 + Parquet I/O
│   │   ├── patterns/        # FVG, BPR, Liquidity 검출 모듈
│   │   ├── backtest/        # BPR 진입 엔진 + 메트릭
│   │   └── models/          # Pydantic 스키마
│   ├── tests/
│   └── data/                # Parquet 파일 저장 디렉토리
└── frontend/
    ├── package.json
    ├── app/                 # Next.js App Router
    │   ├── page.tsx         # 메인 대시보드
    │   └── api/             # (필요 시 BFF)
    ├── components/
    │   ├── chart/           # Lightweight Charts 래퍼
    │   ├── overlays/        # 패턴 오버레이
    │   └── backtest/        # 리포트 UI
    └── lib/
```

## 코딩 컨벤션

### Python (backend)
- 타입 힌트 필수 (`from __future__ import annotations` 사용)
- Pydantic 모델로 데이터 구조 정의 (`models/` 하위)
- 패턴 검출 함수는 순수 함수로 (입력 캔들 DataFrame → 출력 패턴 리스트)
- 모든 패턴 검출 모듈은 `tests/` 에 단위 테스트 1개 이상
- 포매터: `ruff format`, 린터: `ruff check`

### TypeScript (frontend)
- `strict: true`
- 컴포넌트는 함수형 + named export
- 상태관리는 일단 React state로만 (Redux/Zustand 도입 금지 — MVP 범위 초과)
- 스타일: Tailwind 유틸리티 우선, 커스텀 CSS 지양

## 절대 금지 사항

- ❌ 텔레그램 / 알림 / 매매 일지 구현 (Phase 3 작업)
- ❌ 인증/로그인/멀티 유저 기능 (개인용)
- ❌ 사용자가 요청하지 않은 추상화 (예: 거래소 abstract base class — Binance만 쓸 거임)
- ❌ ICT 외 다른 전략 추가 (예: RSI, MACD 보조지표)
- ❌ Docker 컨테이너화 (추후 검토)
- ❌ `docs/` 내용에 모순되는 구현 — 모순 발견 시 작업 멈추고 사용자에게 질문

## 작업 흐름

1. 새 모듈 작성 전: 관련 docs 파일 다시 읽기
2. 패턴 검출 알고리즘은 **반드시 `docs/02_PATTERNS.md` 의 의사 코드와 파라미터값 그대로** 구현
3. BPR 진입 룰은 **반드시 `docs/03_BACKTEST.md`** 따르기
4. 데이터 스키마 변경 필요 시 → `docs/04_DATA_MODEL.md` 먼저 갱신 후 코드 반영
5. 단위 테스트가 통과해야 다음 단계 진행

## 검증 기준 (Phase 1 완료 조건)

- [x] BTCUSDT 1년치 1m/5m/15m/1h/4h 캔들 Parquet 저장 가능
- [x] FVG/IFVG/Swing/Liquidity Pool/Sweep/BPR/Kill Zone 자동 검출
- [x] 검출된 패턴이 차트에 오버레이로 정확히 표시
- [x] 임의 과거 구간에 대해 BPR 룰 백테스트 실행 → 승률, RR, MDD 산출
- [x] 동일 입력 → 동일 백테스트 결과 (재현성)

## 막혔을 때

- 패턴 정의가 모호 → `docs/02_PATTERNS.md` 의 파라미터 섹션 확인
- 진입/청산 룰 모호 → `docs/03_BACKTEST.md` 의 트레이드 라이프사이클 참고
- 둘 다 안 보임 → **임의 결정하지 말고 사용자에게 질문**
