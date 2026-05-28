# 05_ROADMAP.md — 단계별 로드맵

## Phase 1: 백테스팅 코어 (4-6주)

각 주차는 **다음 주차 시작 전 검증 기준 통과 필수**.

---

### Week 1: 데이터 파이프라인

**목표**: Binance에서 캔들 받아서 Parquet에 저장하고 다시 로드.

**작업**
- [ ] `backend/` 디렉토리 셋업 (`pyproject.toml`, `uv`)
- [ ] `app/data/binance.py` — Binance REST 클라이언트 (httpx)
- [ ] `app/data/ingest.py` — CLI 진입점 (`python -m app.data.ingest --symbol BTCUSDT --interval 1h --days 365`)
- [ ] `app/data/loader.py` — Parquet I/O, 기간/심볼 기반 로드 함수
- [ ] 단위 테스트: 캔들 1주일치 수집/저장/로드 round-trip

**검증 기준**
- BTCUSDT 1년치 1h 캔들(약 8760행) 수집 시간 < 30초
- 동일 명령어 재실행 시 중복 행 없음 (upsert 또는 dedup)
- 로드된 DataFrame이 `02_PATTERNS.md` 캔들 스키마와 일치

---

### Week 2: Swing + FVG 검출

**목표**: 가장 단순한 두 패턴 먼저 검증.

**작업**
- [ ] `app/patterns/swings.py` — `detect_swings(candles, N=5)`
- [ ] `app/patterns/fvg.py` — `detect_fvgs`, `update_fvg_states`
- [ ] `app/patterns/atr.py` — Wilder's ATR (FVG 최소 크기 필터용)
- [ ] `tests/fixtures/` — 수동으로 라벨한 작은 캔들 셋 (zigzag, gap 명백한 케이스)
- [ ] 단위 테스트: 알려진 케이스 100% 검출

**검증 기준**
- 수동 라벨한 50개 캔들 시퀀스에서 swing/FVG 검출 일치율 ≥ 95%
- 1년치 1h 캔들에 대해 검출 시간 < 1초

---

### Week 3: IFVG + Liquidity Pool + Sweep + BPR

**목표**: 진입 신호의 근거가 되는 모든 패턴 완성.

**작업**
- [ ] `app/patterns/ifvg.py`
- [ ] `app/patterns/liquidity.py` — Pool 검출 + Sweep 검출
- [ ] `app/patterns/bpr.py`
- [ ] `app/patterns/detect_all.py` — orchestrator (의존성 순서대로 실행)
- [ ] 단위 테스트 추가

**검증 기준**
- 수동 라벨한 BPR 20개 vs 자동 검출 일치율 ≥ 90%
- 1년치 1h 캔들에 대해 전체 패턴 검출 시간 < 3초

---

### Week 4: FastAPI + 차트 + 패턴 오버레이

**목표**: 검출된 패턴을 차트에 시각화.

**작업 (백엔드)**
- [ ] `app/main.py` — FastAPI 앱
- [ ] `app/api/candles.py`, `app/api/patterns.py` — 라우터
- [ ] CORS 설정 (localhost:3000 허용)

**작업 (프론트)**
- [ ] `frontend/` Next.js 셋업, Tailwind, shadcn/ui 초기화
- [ ] `components/chart/CandleChart.tsx` — Lightweight Charts 래퍼
- [ ] `components/overlays/FVGOverlay.tsx` — Bull/Bear 박스 (색상 구분)
- [ ] `components/overlays/BPROverlay.tsx` — 강조 박스
- [ ] `components/overlays/LiquidityOverlay.tsx` — 수평선 + 라벨 (BSL/SSL)
- [ ] `components/overlays/SweepMarker.tsx` — 화살표 마커
- [ ] `components/overlays/KillZoneOverlay.tsx` — 배경 음영
- [ ] `app/page.tsx` — 심볼/타임프레임/기간 선택 + 차트

**검증 기준**
- 차트에 1년치 1h 캔들 + 모든 패턴 오버레이 렌더링 < 2초
- 줌/패닝 시 60fps 유지
- 오버레이가 사용자가 수동으로 본 것과 시각적으로 일치

---

### Week 5: 백테스트 엔진

**목표**: BPR 룰로 트레이드 시뮬레이션 + 메트릭.

**작업**
- [ ] `app/backtest/entry.py` — `find_entry_signal`
- [ ] `app/backtest/stop.py` — `calc_stop_loss`, `calc_take_profit`
- [ ] `app/backtest/simulate.py` — `simulate_trade` (캔들 순회)
- [ ] `app/backtest/engine.py` — 전체 백테스트 실행 + run_id 발급
- [ ] `app/backtest/metrics.py`
- [ ] `app/api/backtest.py` — `POST /api/backtest`
- [ ] SQLite 스키마 마이그레이션 + 저장 로직
- [ ] 단위 테스트 (`03_BACKTEST.md` 의 8가지 케이스)

**검증 기준**
- 동일 입력 두 번 실행 → 동일 메트릭 (재현성)
- 8가지 단위 테스트 모두 통과
- 1년치 백테스트 실행 시간 < 5초

---

### Week 6: 백테스트 UI + 마무리

**목표**: 결과를 차트와 함께 보기.

**작업**
- [ ] `components/backtest/MetricsPanel.tsx` — 승률/PF/MDD 카드
- [ ] `components/backtest/TradesTable.tsx` — 트레이드 목록 (정렬/필터)
- [ ] 차트에 진입/청산 마커 추가 (`EntryMarker`, `ExitMarker`)
- [ ] 파라미터 조정 UI (Swing N, ATR multiplier, BPR overlap ratio 등)
- [ ] [Run Backtest] 버튼 → API 호출 → 결과 표시
- [ ] README 업데이트, 사용 가이드

**검증 기준 (Phase 1 완료)**
- 사용자가 UI만으로 심볼/기간 선택 → 패턴 자동 마킹된 차트 + 백테스트 메트릭 확인 가능
- 수동 차트 분석과 자동 백테스트 결과가 합리적으로 일치

---

## Phase 2: 실시간 분석 + 고급 패턴 (6주)

### Week 1: WebSocket 실시간 데이터

**목표**: Binance WebSocket kline 스트림으로 실시간 캔들 수신.

**작업 (백엔드)**
- [ ] `app/data/ws_binance.py` — Binance `wss://fstream.binance.com/ws/<symbol>@kline_<interval>` 클라이언트
- [ ] `app/api/ws.py` — FastAPI WebSocket 엔드포인트 (`GET /ws/candles`)
- [ ] 신규 캔들 도착 시 Parquet upsert (백그라운드 태스크)

**작업 (프론트)**
- [ ] `lib/ws.ts` — WebSocket 훅 (`useKlineStream`)
- [ ] `page.tsx` — Live/Historical 모드 토글

**검증 기준**
- 브라우저 연결 후 1분 이내 새 캔들 실시간 수신
- 연결 끊김 시 자동 재연결

---

### Week 2: 라이브 차트 + 실시간 패턴 마킹

**목표**: 실시간 캔들에 패턴 자동 재검출 + 차트 반영.

**작업 (백엔드)**
- [ ] `app/backtest/live_detector.py` — 신규 캔들 도착 시 증분 패턴 재검출 (전체 재실행 대신 최근 N캔들만)
- [ ] WebSocket 메시지에 패턴 delta 포함 (`new_fvgs`, `invalidated_fvgs` 등)

**작업 (프론트)**
- [ ] `CandleChart.tsx` — WebSocket 패턴 delta 수신 → 오버레이 증분 업데이트
- [ ] 실시간 모드에서 차트 자동 우측 스크롤

**검증 기준**
- 새 캔들 closed → 2초 이내 패턴 업데이트 반영
- 차트 버벅임 없음 (패턴 재렌더링 < 100ms)

---

### Week 3: PO3 / AMD 패턴 검출

**목표**: Power of 3 (Accumulation → Manipulation → Distribution) 사이클 자동 검출.

**작업 (백엔드)**
- [ ] `app/patterns/po3.py` — `detect_po3(candles, session='london'|'ny')` 구현
  - Accumulation: 좁은 레인지 구간 (ATR 0.5 이하)
  - Manipulation: Liquidity Sweep 발생
  - Distribution: FVG 방향으로 추세 전개
- [ ] `app/patterns/amd.py` — AMD 사이클 검출 (세션별 고/저점 기반)
- [ ] `detect_all.py`에 PO3/AMD 추가
- [ ] 단위 테스트

**작업 (프론트)**
- [ ] `lib/types.ts` — `PO3` 타입 추가
- [ ] 차트 PO3 구간 음영 + A/M/D 레이블

**검증 기준**
- 수동 라벨한 PO3 10개 vs 자동 검출 일치율 ≥ 80%

---

### Week 4: 멀티 타임프레임 분석

**목표**: HTF(1h/4h) BPR + LTF(5m/15m) 진입 신호 연계.

**작업 (백엔드)**
- [ ] `app/backtest/mtf_entry.py` — HTF BPR 영역 내에서 LTF 진입 신호 탐색
- [ ] `POST /api/backtest`에 `htf_interval`, `ltf_interval` 파라미터 추가
- [ ] MTF 백테스트 결과 SQLite 저장

**작업 (프론트)**
- [ ] `page.tsx` — HTF/LTF 인터벌 듀얼 선택 UI
- [ ] 차트에 HTF BPR 박스 + LTF 진입 마커 동시 표시

**검증 기준**
- 1h BPR + 5m 진입 백테스트 정상 실행
- MTF 트레이드 수가 단일 TF보다 적거나 같음 (필터 효과)

---

### Week 5: ICT 7단계 체크리스트 패널

**목표**: 현재 캔들 기준 ICT 진입 조건 자동 평가 패널.

**7단계 체크리스트**
1. Kill Zone 시간대 여부
2. HTF BPR/FVG 근처 여부
3. Liquidity Sweep 발생 여부 (최근 N캔들)
4. BPR 영역 내 close 여부
5. SL 거리 ≤ 3% 여부
6. RR 1:3 TP까지 장애물(다른 BPR) 없음
7. MTF 방향 일치 여부

**작업**
- [ ] `app/api/checklist.py` — `GET /api/checklist` → 현재 캔들 기준 7단계 평가 결과
- [ ] `components/backtest/ChecklistPanel.tsx` — 체크리스트 UI (✓/✗/⚠ 표시)
- [ ] 실시간 모드에서 새 캔들마다 자동 갱신

**검증 기준**
- 알려진 좋은 셋업에서 7/7 통과
- 알려진 나쁜 셋업에서 ≤ 4/7 통과

---

### Week 6: 백테스트 Run 비교 UI

**목표**: 과거 백테스트 run 목록 조회 + 두 run 나란히 비교.

**작업 (백엔드)**
- [ ] `GET /api/backtest/runs` — SQLite `backtest_runs` 목록 조회 (최근 50개)
- [ ] `GET /api/backtest/runs/{run_id}` — 특정 run 트레이드 상세 조회

**작업 (프론트)**
- [ ] `components/backtest/RunHistory.tsx` — run 목록 테이블 (날짜/인터벌/WR/PnL)
- [ ] `components/backtest/RunComparison.tsx` — 두 run 선택 → 메트릭 나란히 비교
- [ ] 선택한 run의 트레이드 마커 차트에 표시

**검증 기준**
- run 목록 로드 < 500ms
- 두 run 비교 시 메트릭 차이 하이라이트 표시

## Phase 3 (예정)

- 텔레그램 봇 알림 (BPR 진입 신호 발생 시)
- 매매 일지 (실전 트레이드 기록 + 백테스트 룰과의 비교)
- 일지 통계 대시보드

---

## 작업 시 체크리스트 (매 PR/커밋)

- [ ] 관련 docs 파일 재확인
- [ ] 단위 테스트 작성/통과
- [ ] `ruff format` + `ruff check` 통과 (Python)
- [ ] `tsc --noEmit` 통과 (TypeScript)
- [ ] 사용자가 요청하지 않은 추상화 추가하지 않음
- [ ] CLAUDE.md 의 "절대 금지 사항" 위반 없음
