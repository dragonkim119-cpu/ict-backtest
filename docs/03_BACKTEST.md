# 03_BACKTEST.md — BPR 백테스트 룰

## 1. 진입 룰 (확정)

### 조건
1. **BPR이 검출되어 있을 것** (`02_PATTERNS.md` 의 BPR 정의 참조)
2. **검출 이후 임의 캔들이 BPR 영역 안에서 close** 해야 함
   - Bullish BPR (롱): `bpr.bottom <= candle.close <= bpr.top`
   - Bearish BPR (숏): `bpr.bottom <= candle.close <= bpr.top`
3. 위 조건을 만족한 캔들의 **다음 캔들 open 가격에 시장가 진입**

### 핵심 원칙
- **확인 대기 (Confirmation)**: wick만 BPR 안에 들어왔다가 close가 밖이면 진입 안 함 → 가짜 터치 필터링
- **Lookahead 금지**: 진입 결정은 close가 확정된 시점에만. 다음 캔들 open으로 진입.

### 의사 코드
```python
def find_entry_signal(bpr: BPR, candles: pd.DataFrame) -> EntrySignal | None:
    for i in range(bpr.created_index + 1, len(candles) - 1):  # 마지막 캔들 제외 (다음 캔들 필요)
        c = candles.iloc[i]
        # BPR 영역 안에 close?
        if bpr.bottom <= c["close"] <= bpr.top:
            next_candle = candles.iloc[i + 1]
            return EntrySignal(
                bpr=bpr,
                trigger_candle_index=i,
                trigger_candle_time=c["open_time"],
                entry_index=i + 1,
                entry_time=next_candle["open_time"],
                entry_price=next_candle["open"],
                direction="long" if bpr.type == "bull" else "short",
            )
        # BPR 무효화: 가격이 BPR을 완전히 뚫고 가버리면 더 이상 유효하지 않음
        if bpr.type == "bull" and c["close"] < bpr.bottom:
            return None  # 무효화
        if bpr.type == "bear" and c["close"] > bpr.top:
            return None
    return None
```

### 중복 진입 방지
- 한 BPR에서 한 번만 진입 (첫 close 신호만)
- 진입이 발생하면 해당 BPR은 "consumed" 상태로 표시

---

## 2. 손절 (SL) — 직전 swing high/low

### 룰
- **롱 진입**: 진입 시점 기준으로 **가장 가까운 과거 swing low** (진입가보다 낮은 것 중)
- **숏 진입**: 진입 시점 기준으로 **가장 가까운 과거 swing high** (진입가보다 높은 것 중)

### 의사 코드
```python
def calc_stop_loss(entry: EntrySignal, swings: list[Swing]) -> float:
    if entry.direction == "long":
        valid = [s for s in swings 
                 if s.type == "low" 
                 and s.index < entry.entry_index 
                 and s.price < entry.entry_price]
        if not valid:
            return None  # 진입 불가 (swing low 없음)
        return min(valid, key=lambda s: entry.entry_index - s.index).price
    else:  # short
        valid = [s for s in swings 
                 if s.type == "high" 
                 and s.index < entry.entry_index 
                 and s.price > entry.entry_price]
        if not valid:
            return None
        return min(valid, key=lambda s: entry.entry_index - s.index).price
```

### SL 안전 마진
- swing 가격을 그대로 SL로 두면 wick에 자주 걸림 → **0.05% 버퍼** 추가
  - 롱: `sl = swing_low * (1 - 0.0005)`
  - 숏: `sl = swing_high * (1 + 0.0005)`

### SL이 비정상적으로 멀 때
- 진입가에서 SL까지 거리가 **진입가의 3% 초과**면 진입 스킵 (RR 비효율)
- 파라미터: `max_sl_distance_pct = 0.03`

---

## 3. 익절 (TP) — 고정 RR 1:3

### 계산
```python
def calc_take_profit(entry_price: float, sl: float, direction: str, rr: float = 3.0) -> float:
    if direction == "long":
        risk = entry_price - sl
        return entry_price + risk * rr
    else:  # short
        risk = sl - entry_price
        return entry_price - risk * rr
```

### 파라미터
- `RISK_REWARD_RATIO = 3.0` (확정값, 추후 UI에서 변경 가능)

---

## 4. 트레이드 라이프사이클

### 상태 머신
```
[BPR 검출]
    ↓
[trigger candle close 발견] → 신호 생성
    ↓
[다음 캔들 open에 진입] → OPEN 상태
    ↓
    ├─→ 캔들 high가 TP 이상 (롱) → CLOSED_WIN
    ├─→ 캔들 low가 SL 이하 (롱)  → CLOSED_LOSS
    └─→ 백테스트 기간 종료      → CLOSED_TIMEOUT
```

### 동일 캔들에서 TP와 SL 둘 다 닿은 경우
- **보수적 가정: SL 우선 적용** (실제 시장에서 worst case)
- 단위 테스트에서 이 케이스를 명시적으로 검증

### 의사 코드
```python
def simulate_trade(entry: EntrySignal, sl: float, tp: float, candles: pd.DataFrame) -> Trade:
    for i in range(entry.entry_index, len(candles)):
        c = candles.iloc[i]
        if entry.direction == "long":
            hit_sl = c["low"] <= sl
            hit_tp = c["high"] >= tp
        else:
            hit_sl = c["high"] >= sl
            hit_tp = c["low"] <= tp
        
        if hit_sl and hit_tp:
            # 보수적: SL 우선
            return Trade(
                entry=entry, sl=sl, tp=tp,
                exit_index=i, exit_time=c["open_time"],
                exit_price=sl, status="closed_loss", pnl_r=-1.0,
            )
        if hit_sl:
            return Trade(
                entry=entry, sl=sl, tp=tp,
                exit_index=i, exit_time=c["open_time"],
                exit_price=sl, status="closed_loss", pnl_r=-1.0,
            )
        if hit_tp:
            return Trade(
                entry=entry, sl=sl, tp=tp,
                exit_index=i, exit_time=c["open_time"],
                exit_price=tp, status="closed_win", pnl_r=3.0,  # RR 1:3
            )
    # 타임아웃 (백테스트 끝까지 미체결)
    last = candles.iloc[-1]
    return Trade(
        entry=entry, sl=sl, tp=tp,
        exit_index=len(candles) - 1, exit_time=last["open_time"],
        exit_price=last["close"], status="closed_timeout",
        pnl_r=compute_unrealized_r(entry, last["close"], sl),
    )
```

### PnL 단위
- `pnl_r` = R-multiple (1R = 진입가-SL 거리)
- 승 = +3R (RR 1:3), 패 = -1R
- 백테스트 메트릭은 R 단위로 집계 (자금 관리 무관하게 룰 자체의 유효성 평가)

---

## 5. 메트릭

### 기본 메트릭
```python
@dataclass
class Metrics:
    total_trades: int
    wins: int
    losses: int
    timeouts: int
    win_rate: float                # wins / (wins + losses), 타임아웃 제외
    profit_factor: float           # 총 수익 R / 총 손실 R 절댓값
    expectancy: float              # 평균 R per trade
    total_pnl_r: float             # 누적 R
    max_drawdown_r: float          # 최대 누적 손실 R
    max_consecutive_losses: int
    avg_trade_duration_candles: float
```

### Drawdown 계산
```python
def compute_max_drawdown(trades: list[Trade]) -> float:
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in trades:
        cumulative += t.pnl_r
        peak = max(peak, cumulative)
        dd = peak - cumulative
        max_dd = max(max_dd, dd)
    return max_dd
```

---

## 6. 추가 필터 (선택, 기본값 OFF)

다음 필터들은 옵션으로 제공하되 **기본 백테스트에는 적용하지 않음**:

| 필터 | 설명 | 기본 |
|---|---|---|
| `kill_zone_only` | Kill Zone 시간대에 발생한 BPR만 사용 | OFF |
| `require_sweep` | BPR 형성 직전 Liquidity Sweep이 있을 때만 진입 | OFF |
| `min_bpr_size_atr` | BPR 높이가 ATR 대비 작으면 스킵 | OFF |

→ 단순 BPR 룰의 raw 성능을 먼저 본 후, 필터 ON/OFF 비교 기능은 UI 토글로 제공.

---

## 7. 백테스트 실행 단위 테스트

| 케이스 | 기대 |
|---|---|
| 단일 Bull BPR 형성 후 1개 trigger candle | 1 trade, 진입가 = 다음 캔들 open |
| Bull BPR + 진입 후 즉시 TP 도달 | win, pnl_r = +3.0 |
| Bull BPR + 진입 후 즉시 SL 도달 | loss, pnl_r = -1.0 |
| 같은 캔들에서 TP, SL 둘 다 터치 | loss (보수적) |
| swing low가 없는 상황의 롱 신호 | 진입 스킵 |
| SL 거리 > 3% | 진입 스킵 |
| 동일 BPR에서 trigger 신호 여러 번 | 첫 번째만 trade 생성 |

---

## 8. Order Block 진입 룰

### BPR 룰과의 공통점 / 차이점

| 항목 | BPR | Order Block |
|---|---|---|
| 진입 구간 | 두 FVG 겹침 영역 | 변위 직전 캔들 바디 |
| 트리거 | OB 범위 안에서 close | OB 범위 안에서 close |
| 진입 | 다음 캔들 open | 다음 캔들 open |
| SL | 직전 swing low/high | OB 하단 아래 (롱) / OB 상단 위 (숏) |
| TP | 1:3 RR | 1:3 RR (동일) |
| 무효화 | close가 BPR 반대로 | close가 OB 바디 반대로 |

### OB 전용 SL 계산

```python
def calc_ob_stop_loss(entry: EntrySignal, ob: OrderBlock) -> float:
    if entry.direction == "long":
        sl = ob.bottom * (1 - 0.0005)   # OB 바디 하단 아래 0.05% 버퍼
    else:
        sl = ob.top * (1 + 0.0005)      # OB 바디 상단 위 0.05% 버퍼
    # SL 거리 3% 초과 시 스킵
    dist_pct = abs(entry.entry_price - sl) / entry.entry_price
    if dist_pct > 0.03:
        return None
    return sl
```

### 의사 코드

```python
def find_ob_entry_signal(ob: OrderBlock, candles: pd.DataFrame) -> EntrySignal | None:
    for i in range(ob.created_index + 1, len(candles) - 1):
        c = candles.iloc[i]
        # OB 범위 안에서 close?
        if ob.bottom <= c["close"] <= ob.top:
            next_candle = candles.iloc[i + 1]
            return EntrySignal(
                bpr=None,           # OB 진입은 bpr=None
                ob=ob,              # OB 참조 추가
                trigger_candle_index=i,
                trigger_candle_time=c["open_time"],
                entry_index=i + 1,
                entry_time=next_candle["open_time"],
                entry_price=next_candle["open"],
                direction="long" if ob.type == "bull" else "short",
            )
        # 무효화
        if ob.type == "bull" and c["close"] < ob.bottom:
            return None
        if ob.type == "bear" and c["close"] > ob.top:
            return None
    return None
```

### 필터 옵션 (BPR과 동일)
- `kill_zone_only`: OB 변위 발생 시점이 Kill Zone 이내일 때만
- `require_sweep`: OB 형성 직전 Sweep 필요
- BPR+OB 동시 활성 시: 두 진입 신호를 **합산**해 백테스트 (중복 진입 방지: 같은 캔들에서 하나만)

---

## 10. 재현성

- 모든 백테스트 결과는 `(symbol, interval, start, end, params_hash)` 로 식별
- SQLite `backtest_runs` 테이블에 결과 + params snapshot 저장
- 동일 입력 → 항상 동일 결과 (랜덤 없음, 외부 API 호출은 데이터 수집 시점에만)
