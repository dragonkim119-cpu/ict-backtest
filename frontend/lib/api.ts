import type { BacktestResponse, CandlesResponse, PatternsResponse } from './types';

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

function qs(params: Record<string, string | undefined>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined) p.set(k, v);
  }
  const s = p.toString();
  return s ? `?${s}` : '';
}

export async function fetchCandles(
  symbol: string,
  interval: string,
  start?: string,
  end?: string,
): Promise<CandlesResponse> {
  const res = await fetch(`${BASE}/api/candles${qs({ symbol, interval, start, end })}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchPatterns(
  symbol: string,
  interval: string,
  start?: string,
  end?: string,
): Promise<PatternsResponse> {
  const res = await fetch(`${BASE}/api/patterns${qs({ symbol, interval, start, end })}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function runBacktest(
  symbol: string,
  interval: string,
  start?: string,
  end?: string,
  killZoneOnly?: boolean,
  requireSweep?: boolean,
  htfInterval?: string,
): Promise<BacktestResponse> {
  const res = await fetch(
    `${BASE}/api/backtest${qs({
      symbol,
      interval,
      start,
      end,
      kill_zone_only: killZoneOnly ? 'true' : undefined,
      require_sweep: requireSweep ? 'true' : undefined,
      htf_interval: htfInterval || undefined,
    })}`,
    { method: 'POST' },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function triggerIngest(
  symbol: string,
  interval: string,
  days: number,
): Promise<{ rows_written: number; latest_time: string | null }> {
  const res = await fetch(`${BASE}/api/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, interval, days }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
