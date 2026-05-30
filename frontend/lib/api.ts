import type {
  BacktestResponse,
  BacktestRun,
  CandleRangeResponse,
  CandlesResponse,
  ChecklistResult,
  JournalCompareResult,
  JournalEntry,
  JournalEntryCreate,
  JournalEntryUpdate,
  JournalStats,
  JournalVsBacktest,
  PatternsResponse,
  RunDetailResponse,
  TurtleDonchianResponse,
} from './types';

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

function qs(params: Record<string, string | undefined>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined) p.set(k, v);
  }
  const s = p.toString();
  return s ? `?${s}` : '';
}

export async function fetchCandleRange(
  symbol: string,
  interval: string,
): Promise<CandleRangeResponse | null> {
  const res = await fetch(`${BASE}/api/candles/range${qs({ symbol, interval })}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(await res.text());
  return res.json();
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

export async function fetchChecklist(
  symbol: string,
  interval: string,
  htfInterval: string = '1h',
): Promise<ChecklistResult> {
  const res = await fetch(
    `${BASE}/api/checklist${qs({ symbol, interval, htf_interval: htfInterval })}`,
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchRuns(limit = 50): Promise<BacktestRun[]> {
  const res = await fetch(`${BASE}/api/backtest/runs${qs({ limit: String(limit) })}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchRunDetail(runId: string): Promise<RunDetailResponse> {
  const res = await fetch(`${BASE}/api/backtest/runs/${encodeURIComponent(runId)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function createJournalEntry(data: JournalEntryCreate): Promise<JournalEntry> {
  const res = await fetch(`${BASE}/api/journal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchJournalEntries(params?: {
  symbol?: string;
  interval?: string;
  direction?: string;
  limit?: number;
}): Promise<JournalEntry[]> {
  const q = qs({
    symbol: params?.symbol,
    interval: params?.interval,
    direction: params?.direction,
    limit: params?.limit !== undefined ? String(params.limit) : undefined,
  });
  const res = await fetch(`${BASE}/api/journal${q}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchJournalEntry(id: number): Promise<JournalEntry> {
  const res = await fetch(`${BASE}/api/journal/${id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateJournalEntry(id: number, data: JournalEntryUpdate): Promise<JournalEntry> {
  const res = await fetch(`${BASE}/api/journal/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteJournalEntry(id: number): Promise<void> {
  const res = await fetch(`${BASE}/api/journal/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(await res.text());
}

export async function compareJournalEntry(id: number): Promise<JournalCompareResult> {
  const res = await fetch(`${BASE}/api/journal/${id}/compare`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchTurtleDonchian(
  symbol: string,
  interval: string,
  start?: string,
  end?: string,
): Promise<TurtleDonchianResponse> {
  const res = await fetch(
    `${BASE}/api/turtle/donchian${qs({ symbol, interval, start, end })}`,
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchJournalStats(): Promise<JournalStats> {
  const res = await fetch(`${BASE}/api/journal/stats`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchJournalVsBacktest(): Promise<JournalVsBacktest> {
  const res = await fetch(`${BASE}/api/journal/compare-backtest`);
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
