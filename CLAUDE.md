# CLAUDE.md — ICT Backtest 프로젝트 컨텍스트

이 문서는 Claude Code가 프로젝트 진입 시 자동으로 참조하는 핵심 컨텍스트 파일입니다.
**작업 전 반드시 이 파일과 `docs/` 디렉토리의 모든 문서를 읽으세요.**

---

## 프로젝트 한 줄 요약

**개인용 ICT/SMC 백테스팅 웹 대시보드** — 비트코인 선물(Binance Futures, BTCUSDT) 과거 데이터에서 ICT 패턴(FVG, BPR, Liquidity Sweep 등)을 자동 검출하고 BPR 진입 룰로 백테스트를 수행합니다.

## 현재 단계

**Phase 1 완료** (2026-05-28 기준) — 전체 6 Week 구현 및 검증 완료.

### Week별 완료 현황

| Week | 내용 | 상태 |
|---|---|---|
| 1 | 프로젝트 셋업, Binance kline 수집, Parquet I/O | ✅ 완료 |
| 2 | FVG / IFVG / Swing High-Low 검출 | ✅ 완료 |
| 3 | Liquidity Pool / Sweep / BPR / Kill Zone 검출 | ✅ 완료 |
| 4 | FastAPI 엔드포인트 + Next.js 차트 + 패턴 오버레이 | ✅ 완료 |
| 5 | 백테스트 엔진 (BPR 진입 룰 + SQLite 저장) | ✅ 완료 |
| 6 | 백테스트 결과 UI (MetricsPanel + TradesTable 마무리) | ✅ 완료 |

### 구현 완료 파일 목록

**Backend**
- `app/data/binance.py` — Binance Futures kline 수집
- `app/data/ingest.py` — 수집 → Parquet upsert
- `app/data/loader.py` — Parquet 로드 (`load_candles`, `_to_utc` 헬퍼)
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
- `app/backtest/engine.py` — `run_backtest` + SQLite 저장
- `app/api/candles.py` — `GET /api/candles`
- `app/api/patterns.py` — `GET /api/patterns`
- `app/api/ingest.py` — `POST /api/ingest`
- `app/api/backtest.py` — `POST /api/backtest`
- `app/main.py` — FastAPI 앱 + CORS

**Frontend**
- `lib/types.ts` — TypeScript 타입 (Candle, FVG, BPR, Trade, Metrics 등)
- `lib/api.ts` — `fetchCandles`, `fetchPatterns`, `runBacktest`, `triggerIngest`
- `lib/chart-primitives.ts` — `BoxesPrimitive`, `KillZonePrimitive` (lightweight-charts v5 ISeriesPrimitive)
- `components/chart/CandleChart.tsx` — 캔들차트 + 패턴 오버레이
- `components/backtest/MetricsPanel.tsx` — 백테스트 메트릭 표시
- `components/backtest/TradesTable.tsx` — 트레이드 목록 테이블
- `app/page.tsx` — 메인 대시보드

**Tests** (79개 전부 통과)
- `tests/test_fvg.py`, `test_ifvg.py`, `test_swings.py`
- `tests/test_liquidity.py` (13개)
- `tests/test_bpr.py` (10개)
- `tests/test_detect_all.py` (8개, 성능 포함)
- `tests/test_backtest.py` (17개)

### 주요 기술 결정 사항 (이전 세션에서 확정)

- **lightweight-charts v5 API**: `chart.addSeries(CandlestickSeries, opts)` (v4의 `addCandlestickSeries` 아님)
- **Sweep 마커**: `createSeriesMarkers<Time>(series, markers)` 사용
- **캔버스 드로잉**: `target.useBitmapCoordinateSpace()` → bitmap 좌표 = media 좌표 × pixelRatio
- **DataFrame 비어있음 체크**: `if candles.empty:` (not `if not candles:`)
- **Timezone**: `load_candles`의 `_to_utc()` 헬퍼 — `ts.tzinfo is None`이면 `tz_localize`, 아니면 `tz_convert`
- **SQLite DB 경로**: `DATA_DIR` 환경변수 (기본 `./data/backtest.db`)

### Week 6 완료 내역

- [x] 백테스트 결과 UI TypeScript 타입 체크 통과 (에러 0)
- [x] 차트 진입/청산 마커 (파란 ▲ 진입, 컬러 ● 청산 — `createSeriesMarkers`)
- [x] 백테스트 필터 UI (`kill_zone_only`, `require_sweep` 체크박스)
- [x] Phase 1 완료 조건 최종 검증 통과

### 추가 기술 결정 사항 (Week 6)

- **백테스트 필터**: `kill_zone_only` — 진입 시점이 Kill Zone 내인지 체크 / `require_sweep` — BPR 생성 전 50캔들 이내 Sweep 존재 여부
- **필터 파라미터 해시 포함**: `_params_hash`에 필터값 포함 → 필터 조합별 고유 `run_id` 보장
- **CORS**: `allow_origins`에 `localhost:3000` + `localhost:3001` 모두 등록
- **서버 실행**: `start.bat` 더블클릭으로 백엔드(8000) + 프론트(3001) 동시 기동

**실시간/알림 기능은 구현하지 마세요**. Phase 2/3 작업입니다.

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

- ❌ Phase 1에서 WebSocket / 실시간 데이터 / 텔레그램 / 알림 시스템 구현
- ❌ 인증/로그인/멀티 유저 기능 (개인용)
- ❌ 사용자가 요청하지 않은 추상화 (예: 거래소 abstract base class — Binance만 쓸 거임)
- ❌ ICT 외 다른 전략 추가 (예: RSI, MACD 보조지표)
- ❌ Docker 컨테이너화 (Phase 1 종료 후 검토)
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
