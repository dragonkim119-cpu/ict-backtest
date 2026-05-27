# 01_SPEC.md — 전체 스펙

## MVP 범위 (Phase 1 한정)

| 기능 | 포함 여부 |
|---|---|
| 과거 캔들 데이터 수집 (Binance) | ✅ |
| 캔들 Parquet 저장/로드 | ✅ |
| FVG 자동 검출 | ✅ |
| IFVG (반전 FVG) 자동 검출 | ✅ |
| Swing High/Low 검출 | ✅ |
| Liquidity Pool 검출 (등가 swing) | ✅ |
| Liquidity Sweep 검출 | ✅ |
| BPR 검출 | ✅ |
| Kill Zone 표시 | ✅ |
| PO3/AMD 자동 검출 | ❌ (Phase 2) |
| 차트 + 자동 오버레이 | ✅ |
| BPR 백테스트 엔진 | ✅ |
| 백테스트 리포트 (승률/RR/MDD) | ✅ |
| 실시간 차트 (WebSocket) | ❌ (Phase 2) |
| 체크리스트 UI | ❌ (Phase 2) |
| 텔레그램/푸시 알림 | ❌ (Phase 3) |
| 매매 일지 기록 | ❌ (Phase 3) |

## 비기능 요구사항

- **단일 사용자**: 인증/세션 없음. localhost 바인딩만.
- **재현성**: 동일 입력 + 동일 룰 → 동일 백테스트 결과 (랜덤 요소 없음).
- **반응성**: 1년치 1h 캔들 차트 로드 < 2초, 패턴 오버레이 렌더링 < 1초.
- **확장성 무시**: 멀티 유저/스케일 고려 안 함 (개인 도구).

## 시스템 아키텍처

```
┌────────────────────────────────────────────────────┐
│                  Frontend (Next.js)                 │
│  ┌──────────────────────────────────────────────┐  │
│  │ ChartView (Lightweight Charts)               │  │
│  │  ├── CandleSeries                            │  │
│  │  ├── FVGOverlay (박스)                        │  │
│  │  ├── BPROverlay (박스 강조)                   │  │
│  │  ├── LiquidityOverlay (수평선)                │  │
│  │  ├── SweepMarker (화살표)                     │  │
│  │  └── KillZoneOverlay (배경 음영)              │  │
│  ├── ControlPanel (심볼/타임프레임/기간 선택)     │  │
│  └── BacktestReport (메트릭 + 트레이드 리스트)    │  │
└────────────────────────────────────────────────────┘
                          ↕ REST (JSON)
┌────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                  │
│  ┌──────────────────────────────────────────────┐  │
│  │ /api/candles      → 캔들 데이터              │  │
│  │ /api/patterns     → 검출된 패턴 일괄         │  │
│  │ /api/backtest     → 백테스트 실행 + 결과     │  │
│  │ /api/ingest       → 신규 데이터 수집 트리거  │  │
│  └──────────────────────────────────────────────┘  │
│                          ↓                          │
│  ┌──────────────────────────────────────────────┐  │
│  │ patterns/  (순수 함수 — 캔들 → 패턴)         │  │
│  │ backtest/  (패턴 → 트레이드 → 메트릭)        │  │
│  │ data/      (Binance API → Parquet)           │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────┐
        │ backend/data/                       │
        │  ├── candles/BTCUSDT_1h.parquet    │
        │  ├── candles/BTCUSDT_5m.parquet    │
        │  └── backtest.sqlite               │
        └─────────────────────────────────────┘
```

## 데이터 흐름 (백테스트 1회 실행 기준)

1. 사용자가 UI에서 심볼(BTCUSDT), 타임프레임(1h), 기간(2024-01-01 ~ 2024-12-31) 선택 후 [Run] 클릭
2. Frontend → `POST /api/backtest` (파라미터 전달)
3. Backend:
   1. `data/loader.py` → Parquet에서 해당 구간 캔들 로드 (없으면 Binance에서 즉시 수집)
   2. `patterns/detect_all.py` → FVG → IFVG → Swing → Liquidity → Sweep → BPR 순으로 검출
   3. `backtest/engine.py` → 시간 순으로 캔들 순회하며 BPR 진입 룰 적용 → 트레이드 리스트 생성
   4. `backtest/metrics.py` → 승률, profit factor, MDD, expectancy 계산
   5. SQLite에 백테스트 결과 저장 (run_id 발급)
4. Frontend ← run_id + 패턴 리스트 + 트레이드 리스트 + 메트릭 응답
5. ChartView 패턴 오버레이 + 트레이드 진입/청산 마커 렌더링
6. BacktestReport 메트릭 + 트레이드 테이블 렌더링

## API 명세 (요약 — 상세는 `04_DATA_MODEL.md` 참조)

### `GET /api/candles`
- Query: `symbol`, `interval`, `start`, `end`
- Response: `{ candles: Candle[] }`

### `GET /api/patterns`
- Query: `symbol`, `interval`, `start`, `end`, `types` (콤마구분: fvg,bpr,liquidity,sweep,killzone)
- Response: `{ fvgs: FVG[], bprs: BPR[], liquidities: Liquidity[], sweeps: Sweep[], killzones: KillZone[] }`

### `POST /api/backtest`
- Body: `{ symbol, interval, start, end, params? }`  (params: RR, swing_lookback 등)
- Response: `{ run_id, trades: Trade[], metrics: Metrics, patterns: {...} }`

### `POST /api/ingest`
- Body: `{ symbol, interval, days }`
- Response: `{ rows_written: number, latest_time: string }`

## 환경 변수 (`.env`)

```
BINANCE_API_BASE=https://fapi.binance.com
DATA_DIR=./backend/data
SQLITE_PATH=./backend/data/backtest.sqlite
```

API 키 불필요 (공개 엔드포인트만 사용).

## 의존성 (확정)

### Python
- fastapi
- uvicorn[standard]
- pandas
- numpy
- pyarrow
- httpx (Binance 요청)
- pydantic
- pytest (테스트)

### Node
- next
- react
- typescript
- tailwindcss
- lightweight-charts (TradingView)
- @radix-ui/* (shadcn 의존)
