'use client';

import dynamic from 'next/dynamic';
import { useState } from 'react';

import { fetchCandles, fetchPatterns, runBacktest, triggerIngest } from '@/lib/api';
import type {
  BPR,
  Candle,
  FVG,
  IFVG,
  KillZoneSpan,
  LiquidityPool,
  Metrics,
  Sweep,
  Trade,
} from '@/lib/types';

import MetricsPanel from '@/components/backtest/MetricsPanel';
import TradesTable from '@/components/backtest/TradesTable';

const CandleChart = dynamic(() => import('@/components/chart/CandleChart'), { ssr: false });

const INTERVALS = ['1m', '5m', '15m', '1h', '4h', '1d'];

interface Visibility {
  fvg: boolean;
  ifvg: boolean;
  bpr: boolean;
  liquidity: boolean;
  sweeps: boolean;
  killzones: boolean;
}

const VISIBILITY_LABELS: { key: keyof Visibility; label: string; color: string }[] = [
  { key: 'fvg', label: 'FVG', color: '#26a69a' },
  { key: 'ifvg', label: 'IFVG', color: '#7c6af7' },
  { key: 'bpr', label: 'BPR', color: '#f59e0b' },
  { key: 'liquidity', label: 'Liquidity', color: '#6b7280' },
  { key: 'sweeps', label: 'Sweeps', color: '#ec4899' },
  { key: 'killzones', label: 'Kill Zones', color: '#374151' },
];

export default function DashboardPage() {
  const [symbol] = useState('BTCUSDT');
  const [interval, setInterval] = useState('1h');
  const [startDate, setStartDate] = useState('2025-06-01');
  const [endDate, setEndDate] = useState('2026-05-26');
  const [visibility, setVisibility] = useState<Visibility>({
    fvg: true,
    ifvg: false,
    bpr: true,
    liquidity: true,
    sweeps: true,
    killzones: true,
  });

  const [candles, setCandles] = useState<Candle[]>([]);
  const [fvgs, setFvgs] = useState<FVG[]>([]);
  const [ifvgs, setIfvgs] = useState<IFVG[]>([]);
  const [bprs, setBprs] = useState<BPR[]>([]);
  const [liquidities, setLiquidities] = useState<LiquidityPool[]>([]);
  const [sweeps, setSweeps] = useState<Sweep[]>([]);
  const [killzones, setKillzones] = useState<KillZoneSpan[]>([]);

  const [btMetrics, setBtMetrics] = useState<Metrics | null>(null);
  const [btTrades, setBtTrades] = useState<Trade[]>([]);
  const [btRunId, setBtRunId] = useState('');
  const [killZoneOnly, setKillZoneOnly] = useState(false);
  const [requireSweep, setRequireSweep] = useState(false);

  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [stats, setStats] = useState('');

  const handleLoad = async () => {
    setStatus('loading');
    setErrorMsg('');
    try {
      const start = startDate ? `${startDate}T00:00:00Z` : undefined;
      const end = endDate ? `${endDate}T23:59:59Z` : undefined;

      const t0 = performance.now();
      const [candleRes, patternRes] = await Promise.all([
        fetchCandles(symbol, interval, start, end),
        fetchPatterns(symbol, interval, start, end),
      ]);
      const elapsed = ((performance.now() - t0) / 1000).toFixed(2);

      setCandles(candleRes.candles);
      setFvgs(patternRes.fvgs);
      setIfvgs(patternRes.ifvgs);
      setBprs(patternRes.bprs);
      setLiquidities(patternRes.liquidities);
      setSweeps(patternRes.sweeps);
      setKillzones(patternRes.killzones);

      setStats(
        `${candleRes.candles.length} candles | ${patternRes.fvgs.length} FVGs | ` +
          `${patternRes.bprs.length} BPRs | ${patternRes.liquidities.length} pools | ` +
          `${patternRes.sweeps.length} sweeps | ${elapsed}s`,
      );
      setStatus('idle');
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
      setStatus('error');
    }
  };

  const handleBacktest = async () => {
    setStatus('loading');
    setErrorMsg('');
    try {
      const start = startDate ? `${startDate}T00:00:00Z` : undefined;
      const end = endDate ? `${endDate}T23:59:59Z` : undefined;
      const result = await runBacktest(symbol, interval, start, end, killZoneOnly, requireSweep);
      setBtMetrics(result.metrics);
      setBtTrades(result.trades);
      setBtRunId(result.run_id);
      setStats(
        `Backtest: ${result.metrics.total_trades} trades | ` +
          `WR ${(result.metrics.win_rate * 100).toFixed(1)}% | ` +
          `PF ${result.metrics.profit_factor === Infinity ? '∞' : result.metrics.profit_factor.toFixed(2)} | ` +
          `${result.metrics.total_pnl_r.toFixed(2)}R total`,
      );
      setStatus('idle');
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
      setStatus('error');
    }
  };

  const handleIngest = async () => {
    setStatus('loading');
    setErrorMsg('');
    try {
      const result = await triggerIngest(symbol, interval, 365);
      setStats(`Ingested ${result.rows_written} rows. Latest: ${result.latest_time ?? 'n/a'}`);
      setStatus('idle');
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
      setStatus('error');
    }
  };

  const toggleVisibility = (key: keyof Visibility) => {
    setVisibility((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <main className="min-h-screen p-4" style={{ background: '#0d0f17' }}>
      <h1 className="text-xl font-bold text-white mb-4">ICT Backtest Dashboard</h1>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mb-3">
        <span className="px-3 py-1.5 rounded text-white text-sm font-mono bg-[#1e2130]">
          {symbol}
        </span>

        <select
          value={interval}
          onChange={(e) => setInterval(e.target.value)}
          className="px-3 py-1.5 rounded bg-[#1e2130] text-white text-sm border border-[#2a2e39]"
        >
          {INTERVALS.map((i) => (
            <option key={i} value={i}>
              {i}
            </option>
          ))}
        </select>

        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          className="px-3 py-1.5 rounded bg-[#1e2130] text-white text-sm border border-[#2a2e39]"
        />
        <span className="text-gray-500 text-sm">→</span>
        <input
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          className="px-3 py-1.5 rounded bg-[#1e2130] text-white text-sm border border-[#2a2e39]"
        />

        <button
          onClick={handleLoad}
          disabled={status === 'loading'}
          className="px-4 py-1.5 rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-semibold transition-colors"
        >
          {status === 'loading' ? 'Loading…' : 'Load Chart'}
        </button>
        <button
          onClick={handleBacktest}
          disabled={status === 'loading'}
          className="px-4 py-1.5 rounded bg-purple-700 hover:bg-purple-600 disabled:opacity-50 text-white text-sm font-semibold transition-colors"
        >
          Run Backtest
        </button>
        <button
          onClick={handleIngest}
          disabled={status === 'loading'}
          className="px-4 py-1.5 rounded bg-[#2a2e39] hover:bg-[#363c4e] disabled:opacity-50 text-gray-300 text-sm transition-colors"
        >
          Ingest Data
        </button>

        <label className="flex items-center gap-1.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={killZoneOnly}
            onChange={(e) => setKillZoneOnly(e.target.checked)}
            className="accent-purple-500"
          />
          <span className="text-xs text-gray-400">KZ Only</span>
        </label>
        <label className="flex items-center gap-1.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={requireSweep}
            onChange={(e) => setRequireSweep(e.target.checked)}
            className="accent-purple-500"
          />
          <span className="text-xs text-gray-400">Req. Sweep</span>
        </label>
      </div>

      {/* Visibility toggles */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span className="text-xs text-gray-500">Show:</span>
        {VISIBILITY_LABELS.map(({ key, label, color }) => (
          <button
            key={key}
            onClick={() => toggleVisibility(key)}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors border ${
              visibility[key]
                ? 'text-white border-transparent'
                : 'text-gray-500 border-[#2a2e39] bg-transparent'
            }`}
            style={visibility[key] ? { backgroundColor: color } : undefined}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Status */}
      {stats && <p className="mb-2 text-xs text-gray-400 font-mono">{stats}</p>}
      {errorMsg && <p className="mb-2 text-xs text-red-400 font-mono">Error: {errorMsg}</p>}

      {/* Chart */}
      <CandleChart
        candles={candles}
        fvgs={fvgs}
        ifvgs={ifvgs}
        bprs={bprs}
        liquidities={liquidities}
        sweeps={sweeps}
        killzones={killzones}
        visibility={visibility}
        trades={btTrades}
      />

      {/* Backtest results */}
      {btMetrics && (
        <div className="mt-4 flex flex-col gap-3">
          <MetricsPanel metrics={btMetrics} runId={btRunId} />
          <TradesTable trades={btTrades} />
        </div>
      )}

      {/* Legend */}
      <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-500">
        <span>
          <span className="inline-block w-3 h-3 mr-1 align-middle rounded-sm" style={{ background: 'rgba(38,166,154,0.4)' }} />
          Bull FVG / BPR
        </span>
        <span>
          <span className="inline-block w-3 h-3 mr-1 align-middle rounded-sm" style={{ background: 'rgba(239,83,80,0.4)' }} />
          Bear FVG / BPR
        </span>
        <span className="text-green-500">— SSL</span>
        <span className="text-red-500">— BSL</span>
        <span>▲ Bull Sweep &nbsp; ▼ Bear Sweep</span>
      </div>
    </main>
  );
}
