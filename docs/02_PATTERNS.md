# 02_PATTERNS.md — 패턴 검출 알고리즘

이 문서는 **각 ICT 패턴의 검출 룰을 코드로 옮길 수 있을 만큼 명확하게** 정의합니다.
Claude Code는 여기 의사 코드와 파라미터값을 **그대로** 구현하세요.

---

## 검출 순서 (의존성)

```
1. Swing High/Low      ← 캔들만 필요
2. FVG (Bullish/Bear)  ← 캔들만 필요
3. IFVG                ← FVG 결과 필요
4. Liquidity Pool      ← Swing 결과 필요
5. Liquidity Sweep     ← Swing + 캔들 필요
6. BPR                 ← FVG 결과 필요
7. Kill Zone           ← 시간만 필요 (캔들 불필요)
```

각 모듈은 **순수 함수**: 입력은 `pd.DataFrame` (캔들), 출력은 `List[Pattern]`.

---

## 공통 캔들 스키마

모든 검출 함수의 입력은 다음 컬럼을 가진 `pd.DataFrame`:

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `open_time` | datetime64[ns, UTC] | 캔들 시작 시간 |
| `open` | float | 시가 |
| `high` | float | 고가 |
| `low` | float | 저가 |
| `close` | float | 종가 |
| `volume` | float | 거래량 |

인덱스는 0부터 시작하는 정수. `open_time` 오름차순 정렬.

---

## 1. Swing High / Low

### 정의
- **Swing High**: 좌측 N개, 우측 N개 캔들의 high보다 자기 자신의 high가 큰 캔들
- **Swing Low**: 좌측 N개, 우측 N개 캔들의 low보다 자기 자신의 low가 작은 캔들

### 파라미터
- `N = 5` (기본값, 사용자 조정 가능)

### 의사 코드
```python
def detect_swings(candles: pd.DataFrame, N: int = 5) -> list[Swing]:
    swings = []
    for i in range(N, len(candles) - N):
        window_high = candles.iloc[i-N:i+N+1]
        if candles.iloc[i]["high"] == window_high["high"].max():
            # 동률이 여러 개일 수 있으니 첫 번째만 채택
            if not any(s.index == i for s in swings):
                swings.append(Swing(
                    index=i,
                    type="high",
                    price=candles.iloc[i]["high"],
                    time=candles.iloc[i]["open_time"],
                ))
        window_low = candles.iloc[i-N:i+N+1]
        if candles.iloc[i]["low"] == window_low["low"].min():
            swings.append(Swing(
                index=i,
                type="low",
                price=candles.iloc[i]["low"],
                time=candles.iloc[i]["open_time"],
            ))
    return swings
```

### 주의
- 마지막 N개 캔들은 swing 판정 불가 (우측 확인 캔들 부족) — 무시
- swing은 **확정** 시점에만 생성 (i+N 캔들까지 봐야 확정)

---

## 2. FVG (Fair Value Gap)

### 정의
3개 연속 캔들에서 가운데 캔들이 비효율적인 가격 이동을 일으켜 좌우 캔들 사이에 갭이 생긴 영역.

- **Bullish FVG**: `candle[i-2].high < candle[i].low`
  - 갭 영역: `[candle[i-2].high, candle[i].low]` (bottom, top)
  - 의미: 빠른 상승 → 향후 매수 지지 역할 기대

- **Bearish FVG**: `candle[i-2].low > candle[i].high`
  - 갭 영역: `[candle[i].high, candle[i-2].low]` (bottom, top)
  - 의미: 빠른 하락 → 향후 매도 저항 역할 기대

> 비유: FVG는 **눈길에 뛰어간 발자국 사이의 빈 공간**. 발자국 채우러 돌아올 가능성 높음.

### 파라미터
- 최소 갭 크기: ATR(14) × 0.1 이상만 유효 FVG로 채택 (노이즈 필터링)
  - `atr_multiplier = 0.1` (기본값)

### 의사 코드
```python
def detect_fvgs(candles: pd.DataFrame, atr_multiplier: float = 0.1) -> list[FVG]:
    atr = compute_atr(candles, period=14)  # pd.Series, len = len(candles)
    fvgs = []
    for i in range(2, len(candles)):
        c_prev = candles.iloc[i-2]
        c_curr = candles.iloc[i]
        c_mid = candles.iloc[i-1]
        min_gap = atr.iloc[i] * atr_multiplier

        # Bullish FVG
        if c_prev["high"] < c_curr["low"] and (c_curr["low"] - c_prev["high"]) >= min_gap:
            fvgs.append(FVG(
                type="bull",
                bottom=c_prev["high"],
                top=c_curr["low"],
                start_index=i-2,
                middle_index=i-1,
                end_index=i,
                created_time=c_mid["open_time"],
                mitigated=False,
                mitigated_time=None,
                invalidated=False,
                invalidated_time=None,
            ))
        # Bearish FVG
        elif c_prev["low"] > c_curr["high"] and (c_prev["low"] - c_curr["high"]) >= min_gap:
            fvgs.append(FVG(
                type="bear",
                bottom=c_curr["high"],
                top=c_prev["low"],
                start_index=i-2,
                middle_index=i-1,
                end_index=i,
                created_time=c_mid["open_time"],
                mitigated=False, mitigated_time=None,
                invalidated=False, invalidated_time=None,
            ))
    return fvgs
```

### FVG 상태 추적 (Mitigation / Invalidation)

생성된 FVG는 이후 캔들에 따라 상태가 변함:

```python
def update_fvg_states(fvgs: list[FVG], candles: pd.DataFrame) -> list[FVG]:
    for fvg in fvgs:
        for i in range(fvg.end_index + 1, len(candles)):
            c = candles.iloc[i]
            if fvg.type == "bull":
                # Mitigated: low가 FVG 안으로 들어옴 (터치)
                if not fvg.mitigated and c["low"] <= fvg.top:
                    fvg.mitigated = True
                    fvg.mitigated_time = c["open_time"]
                # Invalidated: close가 FVG 아래로 (bull FVG가 뚫림)
                if not fvg.invalidated and c["close"] < fvg.bottom:
                    fvg.invalidated = True
                    fvg.invalidated_time = c["open_time"]
                    break  # 더 추적 안 함
            else:  # bear
                if not fvg.mitigated and c["high"] >= fvg.bottom:
                    fvg.mitigated = True
                    fvg.mitigated_time = c["open_time"]
                if not fvg.invalidated and c["close"] > fvg.top:
                    fvg.invalidated = True
                    fvg.invalidated_time = c["open_time"]
                    break
    return fvgs
```

---

## 3. IFVG (Inversion FVG)

### 정의
**Invalidated된 FVG는 반대 방향의 IFVG로 전환됨.**
- Bullish FVG가 invalidated (close가 아래로) → **Bearish IFVG** (저항 역할)
- Bearish FVG가 invalidated (close가 위로) → **Bullish IFVG** (지지 역할)

### 의사 코드
```python
def derive_ifvgs(fvgs: list[FVG]) -> list[IFVG]:
    ifvgs = []
    for fvg in fvgs:
        if not fvg.invalidated:
            continue
        ifvgs.append(IFVG(
            original_fvg=fvg,
            type="bear" if fvg.type == "bull" else "bull",
            bottom=fvg.bottom,
            top=fvg.top,
            created_time=fvg.invalidated_time,
        ))
    return ifvgs
```

---

## 4. Liquidity Pool

### 정의
유사한 가격에 형성된 swing high/low의 군집 — 손절 주문이 쌓여있을 가능성이 큰 영역.

- **BSL (Buy-Side Liquidity)**: 등가 swing high들 → 가격 상단의 매수 청산 주문 풀
- **SSL (Sell-Side Liquidity)**: 등가 swing low들 → 가격 하단의 매도 청산 주문 풀

### 파라미터
- `tolerance = 0.001` (0.1%) — 두 swing 가격 차이가 이 이내면 등가로 간주
- `min_count = 2` — 최소 swing 개수

### 의사 코드
```python
def detect_liquidity_pools(swings: list[Swing], tolerance: float = 0.001, min_count: int = 2) -> list[LiquidityPool]:
    pools = []
    for swing_type in ("high", "low"):
        sub = sorted([s for s in swings if s.type == swing_type], key=lambda s: s.price)
        # 가격 순 정렬 후 인접한 것끼리 클러스터링
        clusters = []
        current = [sub[0]] if sub else []
        for s in sub[1:]:
            if abs(s.price - current[-1].price) / current[-1].price <= tolerance:
                current.append(s)
            else:
                if len(current) >= min_count:
                    clusters.append(current)
                current = [s]
        if len(current) >= min_count:
            clusters.append(current)

        for cluster in clusters:
            pools.append(LiquidityPool(
                side="BSL" if swing_type == "high" else "SSL",
                level=sum(s.price for s in cluster) / len(cluster),  # 평균가
                swings=cluster,
                swept=False,
                swept_time=None,
            ))
    return pools
```

---

## 5. Liquidity Sweep

### 정의
가격이 liquidity pool 레벨을 wick으로 돌파했다가 close는 반대로 돌아오는 캔들 → 유동성을 "쓸어간" 행위.

- **BSL Sweep (bearish)**: `candle.high > pool.level` AND `candle.close < pool.level`
- **SSL Sweep (bullish)**: `candle.low < pool.level` AND `candle.close > pool.level`

### 의사 코드
```python
def detect_sweeps(pools: list[LiquidityPool], candles: pd.DataFrame) -> list[Sweep]:
    sweeps = []
    for pool in pools:
        # pool의 마지막 swing 이후의 캔들만 검사
        last_swing_index = max(s.index for s in pool.swings)
        for i in range(last_swing_index + 1, len(candles)):
            c = candles.iloc[i]
            if pool.side == "BSL" and c["high"] > pool.level and c["close"] < pool.level:
                pool.swept = True
                pool.swept_time = c["open_time"]
                sweeps.append(Sweep(
                    type="bear",  # BSL 쓸린 후 → 하락 셋업
                    pool=pool,
                    sweep_index=i,
                    sweep_time=c["open_time"],
                    sweep_high=c["high"],
                ))
                break
            elif pool.side == "SSL" and c["low"] < pool.level and c["close"] > pool.level:
                pool.swept = True
                pool.swept_time = c["open_time"]
                sweeps.append(Sweep(
                    type="bull",
                    pool=pool,
                    sweep_index=i,
                    sweep_time=c["open_time"],
                    sweep_low=c["low"],
                ))
                break
    return sweeps
```

---

## 6. BPR (Balanced Price Range) ⭐ 진입 기준

### 정의
**같은 가격대에서 형성된 반대 방향 FVG 2개의 겹침 영역.**
- "한쪽 세력이 패배하고 반대편이 장악한 자리" → 강한 지지/저항 영역
- A+ 셋업의 핵심 진입 영역

### 형성 조건
1. 먼저 생성된 FVG (**fvg_old**)
2. 그 후 시간상 나중에 생성된 반대 방향 FVG (**fvg_new**)
3. 둘의 가격 범위가 겹침 (overlap > 0)
4. fvg_new의 방향이 BPR의 방향성을 결정 (fvg_new가 bull → Bullish BPR)

### 파라미터
- `min_overlap_ratio = 0.3` — overlap이 두 FVG 중 작은 쪽의 30% 이상이어야 유효 BPR
- `max_age_candles = 100` — fvg_new가 fvg_old의 100캔들 이내에 생성되어야 함

### 의사 코드
```python
def detect_bprs(fvgs: list[FVG], max_age_candles: int = 100, min_overlap_ratio: float = 0.3) -> list[BPR]:
    bprs = []
    fvgs_sorted = sorted(fvgs, key=lambda f: f.middle_index)
    for i, fvg_new in enumerate(fvgs_sorted):
        for fvg_old in fvgs_sorted[:i]:
            if fvg_old.type == fvg_new.type:
                continue  # 반대 방향이어야 함
            if fvg_new.middle_index - fvg_old.middle_index > max_age_candles:
                continue
            # overlap 계산
            overlap_top = min(fvg_old.top, fvg_new.top)
            overlap_bottom = max(fvg_old.bottom, fvg_new.bottom)
            overlap = overlap_top - overlap_bottom
            if overlap <= 0:
                continue
            smaller = min(fvg_old.top - fvg_old.bottom, fvg_new.top - fvg_new.bottom)
            if overlap / smaller < min_overlap_ratio:
                continue
            bprs.append(BPR(
                type=fvg_new.type,  # 새 FVG 방향이 BPR 방향
                top=overlap_top,
                bottom=overlap_bottom,
                fvg_old=fvg_old,
                fvg_new=fvg_new,
                created_time=fvg_new.created_time,
                created_index=fvg_new.end_index,
            ))
    return bprs
```

### 주의
- BPR은 fvg_new가 확정된 시점 이후 캔들에서만 진입 후보 (lookahead bias 방지)
- 진입 룰은 `03_BACKTEST.md` 참조

---

## 7. Kill Zone

### 정의
유동성과 변동성이 집중되는 세션 오프닝 시간대. 자동 검출이 아닌 **시간 필터**.

### 시간대 (UTC 기준)

| 이름 | UTC 시간 | 비고 |
|---|---|---|
| Asia | 23:00 – 04:00 | 거래량 낮음 — MVP에선 표시만 |
| London Open | 02:00 – 05:00 | 핵심 |
| New York AM | 13:30 – 16:00 | 핵심 |
| New York PM | 18:00 – 20:00 | 부가 |

### 의사 코드
```python
KILL_ZONES = [
    ("Asia", 23, 0, 4, 0),
    ("London", 2, 0, 5, 0),
    ("NY_AM", 13, 30, 16, 0),
    ("NY_PM", 18, 0, 20, 0),
]

def detect_killzones(candles: pd.DataFrame) -> list[KillZoneSpan]:
    """각 캔들이 어느 kill zone에 속하는지 라벨링."""
    spans = []
    for name, sh, sm, eh, em in KILL_ZONES:
        in_zone = candles["open_time"].dt.hour.between(sh, eh, inclusive="left") \
                  & (some_minute_logic_TODO)
        # 단순 구현: 시간만 비교 (분 단위 정밀화는 필요 시 추가)
        # ... start/end 인덱스 식별 후 KillZoneSpan으로 묶음
    return spans
```

> 구현 노트: 자정을 가로지르는 Asia 세션은 `(hour >= 23 or hour < 4)` 로 처리.

---

## 파라미터 요약 (한 곳에 모음)

```python
# patterns/config.py
SWING_LOOKBACK = 5
FVG_ATR_MULTIPLIER = 0.1
LIQUIDITY_TOLERANCE = 0.001  # 0.1%
LIQUIDITY_MIN_COUNT = 2
BPR_MAX_AGE_CANDLES = 100
BPR_MIN_OVERLAP_RATIO = 0.3
ATR_PERIOD = 14
```

**모든 파라미터는 추후 UI에서 조정 가능하도록 API로 노출 (Phase 1 후반).**

---

## 단위 테스트 요구사항

각 검출 함수는 다음 케이스를 통과해야 함:

| 함수 | 테스트 케이스 |
|---|---|
| `detect_swings` | 단조증가 캔들 → swing 0개 / 인공 zigzag → 정확한 swing 개수 |
| `detect_fvgs` | 명백한 bull/bear 갭 캔들 시퀀스 → 정확히 1개 검출 |
| `update_fvg_states` | mitigation 발생 시 플래그, invalidation 후 추적 중단 |
| `detect_liquidity_pools` | 등가 swing 3개 → 1개 풀 / 가격 차이 큰 swing → 0개 |
| `detect_sweeps` | wick만 돌파한 캔들 → sweep / close까지 돌파 → sweep 아님 |
| `detect_bprs` | 반대 방향 FVG 겹침 → BPR / 같은 방향 → BPR 아님 |

테스트 데이터는 `tests/fixtures/` 에 작은 CSV로 보관.
