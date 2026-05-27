# 04_DATA_MODEL.md — 데이터 스키마

## 1. 캔들 (Parquet)

### 파일 경로
```
backend/data/candles/{symbol}_{interval}.parquet
# 예: backend/data/candles/BTCUSDT_1h.parquet
```

### 스키마 (pyarrow)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `open_time` | `timestamp[ms, tz=UTC]` | 캔들 시작 (Binance에서 ms 단위) |
| `open` | `float64` | |
| `high` | `float64` | |
| `low` | `float64` | |
| `close` | `float64` | |
| `volume` | `float64` | |
| `close_time` | `timestamp[ms, tz=UTC]` | |
| `quote_volume` | `float64` | |
| `trades` | `int64` | |

### Binance 응답 매핑
Binance `/fapi/v1/klines` 응답은 배열 형태:
```python
COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]
# 첫 9개만 사용, 뒤 3개 drop
```

### 인덱싱
- 파일 로드 후 `open_time` 기준 정렬 + 중복 제거
- Pandas 인덱스는 정수 (RangeIndex) 유지

---

## 2. Pydantic 모델 (백엔드 → 프론트엔드 JSON)

### `backend/app/models/candle.py`
```python
from pydantic import BaseModel
from datetime import datetime

class Candle(BaseModel):
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
```

### `backend/app/models/patterns.py`
```python
from typing import Literal
from pydantic import BaseModel
from datetime import datetime

class Swing(BaseModel):
    index: int
    type: Literal["high", "low"]
    price: float
    time: datetime

class FVG(BaseModel):
    type: Literal["bull", "bear"]
    bottom: float
    top: float
    start_index: int
    middle_index: int
    end_index: int
    created_time: datetime
    mitigated: bool = False
    mitigated_time: datetime | None = None
    invalidated: bool = False
    invalidated_time: datetime | None = None

class IFVG(BaseModel):
    type: Literal["bull", "bear"]
    bottom: float
    top: float
    created_time: datetime
    original_fvg_created_time: datetime  # 원본 FVG 추적용

class LiquidityPool(BaseModel):
    side: Literal["BSL", "SSL"]
    level: float
    swing_times: list[datetime]
    swept: bool = False
    swept_time: datetime | None = None

class Sweep(BaseModel):
    type: Literal["bull", "bear"]
    pool_level: float
    sweep_index: int
    sweep_time: datetime
    sweep_extreme: float  # bull이면 sweep_low, bear면 sweep_high

class BPR(BaseModel):
    type: Literal["bull", "bear"]
    top: float
    bottom: float
    fvg_old_time: datetime
    fvg_new_time: datetime
    created_time: datetime  # = fvg_new.created_time
    created_index: int

class KillZoneSpan(BaseModel):
    name: Literal["Asia", "London", "NY_AM", "NY_PM"]
    start_time: datetime
    end_time: datetime
```

### `backend/app/models/trade.py`
```python
class EntrySignal(BaseModel):
    bpr_created_time: datetime
    trigger_candle_time: datetime
    entry_index: int
    entry_time: datetime
    entry_price: float
    direction: Literal["long", "short"]

class Trade(BaseModel):
    id: str  # uuid
    direction: Literal["long", "short"]
    entry_time: datetime
    entry_price: float
    sl: float
    tp: float
    exit_time: datetime | None
    exit_price: float | None
    status: Literal["open", "closed_win", "closed_loss", "closed_timeout"]
    pnl_r: float
    bpr_created_time: datetime
    trigger_candle_time: datetime
    duration_candles: int | None

class Metrics(BaseModel):
    total_trades: int
    wins: int
    losses: int
    timeouts: int
    win_rate: float
    profit_factor: float
    expectancy: float
    total_pnl_r: float
    max_drawdown_r: float
    max_consecutive_losses: int
    avg_trade_duration_candles: float
```

---

## 3. SQLite 스키마 (백테스트 결과 보관)

### `backend/data/backtest.sqlite`

```sql
CREATE TABLE backtest_runs (
    run_id          TEXT PRIMARY KEY,  -- uuid
    symbol          TEXT NOT NULL,
    interval        TEXT NOT NULL,
    start_time      TEXT NOT NULL,     -- ISO8601 UTC
    end_time        TEXT NOT NULL,
    params_json     TEXT NOT NULL,     -- 모든 파라미터 snapshot
    params_hash     TEXT NOT NULL,     -- 재현성 식별용
    created_at      TEXT NOT NULL,
    metrics_json    TEXT NOT NULL      -- Metrics 직렬화
);

CREATE INDEX idx_runs_lookup 
    ON backtest_runs (symbol, interval, start_time, end_time, params_hash);

CREATE TABLE backtest_trades (
    trade_id        TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL REFERENCES backtest_runs(run_id),
    direction       TEXT NOT NULL,
    entry_time      TEXT NOT NULL,
    entry_price     REAL NOT NULL,
    sl              REAL NOT NULL,
    tp              REAL NOT NULL,
    exit_time       TEXT,
    exit_price      REAL,
    status          TEXT NOT NULL,
    pnl_r           REAL NOT NULL,
    bpr_created_time     TEXT NOT NULL,
    trigger_candle_time  TEXT NOT NULL,
    duration_candles     INTEGER
);

CREATE INDEX idx_trades_run ON backtest_trades (run_id);
```

> Phase 1에선 단일 run만 동시 실행. 멀티 run 비교 UI는 Phase 1 후반 또는 Phase 2.

---

## 4. API 응답 포맷 예시

### `GET /api/patterns`
```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "start": "2024-01-01T00:00:00Z",
  "end": "2024-12-31T23:00:00Z",
  "fvgs": [
    {"type": "bull", "top": 42500.0, "bottom": 42300.0, "created_time": "2024-01-15T03:00:00Z", "mitigated": true, ...}
  ],
  "ifvgs": [...],
  "bprs": [
    {"type": "bull", "top": 42400.0, "bottom": 42350.0, "created_time": "2024-01-16T10:00:00Z", ...}
  ],
  "liquidities": [...],
  "sweeps": [...],
  "killzones": [...]
}
```

### `POST /api/backtest`
```json
{
  "run_id": "a3f2b1...",
  "metrics": {
    "total_trades": 42,
    "wins": 14,
    "losses": 26,
    "win_rate": 0.35,
    "expectancy": 0.4,
    "profit_factor": 1.61,
    "total_pnl_r": 16.8,
    "max_drawdown_r": 5.2,
    ...
  },
  "trades": [...],
  "patterns": { ... }   // /api/patterns와 동일 구조
}
```

---

## 5. 프론트엔드 타입 (TypeScript)

`frontend/lib/types.ts` 에 백엔드 Pydantic 모델 1:1 미러:
```typescript
export type Candle = {
  open_time: string;  // ISO8601
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type FVG = {
  type: "bull" | "bear";
  top: number;
  bottom: number;
  created_time: string;
  mitigated: boolean;
  mitigated_time: string | null;
  invalidated: boolean;
  invalidated_time: string | null;
  start_index: number;
  middle_index: number;
  end_index: number;
};

// ... BPR, Sweep, Trade 등 동일 패턴
```

> 가능하면 백엔드에서 OpenAPI schema export → `openapi-typescript` 로 자동 생성하는 것 권장 (수동 동기화 부담 제거).
