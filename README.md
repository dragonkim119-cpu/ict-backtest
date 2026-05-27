# ICT Backtest

비트코인 선물(Binance Futures BTCUSDT) 과거 데이터에서 ICT/SMC 패턴(FVG, BPR, Liquidity Sweep 등)을 자동 검출하고 BPR 진입 룰로 백테스트하는 **개인용 웹 대시보드**.

## Why

영상에서 본 ICT 기법(`https://www.youtube.com/watch?v=gcrJXbmNWFY`)을 수동으로 적용하면 다음 한계가 있음:
- 차트마다 FVG/BPR/Liquidity 찾는 데 시간 소요
- 룰을 일관되게 적용하기 어려움
- 백테스트로 검증 없이 실전 적용 위험

→ 자동 검출 + 백테스트로 룰의 통계적 유효성을 먼저 검증.

## Tech Stack

- **Backend**: Python 3.11 + FastAPI + pandas/numpy + pyarrow
- **Frontend**: Next.js 14 + TypeScript + Tailwind + shadcn/ui
- **Chart**: TradingView Lightweight Charts
- **Storage**: Parquet (캔들) + SQLite (백테스트/일지)
- **Data**: Binance Futures REST API

## Quick Start

```bash
# Backend
cd backend
uv sync
uv run python -m app.data.ingest --symbol BTCUSDT --interval 1h --days 365
uv run uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
pnpm install
pnpm dev
# → http://localhost:3000
```

## 문서

- [`CLAUDE.md`](./CLAUDE.md) — Claude Code용 컨텍스트
- [`docs/01_SPEC.md`](./docs/01_SPEC.md) — 전체 스펙
- [`docs/02_PATTERNS.md`](./docs/02_PATTERNS.md) — 패턴 검출 알고리즘
- [`docs/03_BACKTEST.md`](./docs/03_BACKTEST.md) — BPR 백테스트 룰
- [`docs/04_DATA_MODEL.md`](./docs/04_DATA_MODEL.md) — 데이터 스키마
- [`docs/05_ROADMAP.md`](./docs/05_ROADMAP.md) — Phase별 로드맵

## Status

Phase 1 (백테스팅 코어) — 개발 중
