'use client';

import dynamic from 'next/dynamic';
import { useEffect, useMemo, useState } from 'react';

import {
  fetchCandleRange,
  fetchCandles,
  fetchChecklist,
  fetchPatterns,
  fetchRunDetail,
  fetchRuns,
  fetchTurtleDonchian,
  runBacktest,
  triggerIngest,
} from '@/lib/api';
import type {
  BPR,
  BacktestRun,
  Candle,
  ChecklistResult,
  FVG,
  IFVG,
  KillZoneSpan,
  LiquidityPool,
  Metrics,
  PO3,
  StoredTrade,
  Sweep,
  Trade,
  TurtleDonchianResponse,
} from '@/lib/types';
import { useKlineStream } from '@/lib/ws';

import ChecklistPanel from '@/components/backtest/ChecklistPanel';
import MetricsPanel from '@/components/backtest/MetricsPanel';
import RunComparison from '@/components/backtest/RunComparison';
import RunHistory from '@/components/backtest/RunHistory';
import TradesTable from '@/components/backtest/TradesTable';
import JournalTab from '@/components/journal/JournalTab';
import MacroTab from '@/components/macro/MacroTab';

const CandleChart = dynamic(() => import('@/components/chart/CandleChart'), { ssr: false });

const INTERVALS = ['1m', '5m', '15m', '1h', '4h', '1d'];

const WS_STATUS_STYLE: Record<string, string> = {
  connected: 'text-green-400',
  connecting: 'text-yellow-400',
  error: 'text-red-400',
  disconnected: 'text-gray-500',
};

const WS_STATUS_LABEL: Record<string, string> = {
  connected: '● LIVE',
  connecting: '◌ connecting…',
  error: '✕ WS error',
  disconnected: '',
};

interface Visibility {
  fvg: boolean;
  ifvg: boolean;
  bpr: boolean;
  liquidity: boolean;
  sweeps: boolean;
  killzones: boolean;
  po3: boolean;
  turtle_s1: boolean;
  turtle_s2: boolean;
  ma20: boolean;
  ma50: boolean;
  ma200: boolean;
  ema50: boolean;
  vwap: boolean;
  volume: boolean;
}

const VISIBILITY_LABELS: { key: keyof Visibility; label: string; color: string }[] = [
  { key: 'fvg', label: 'FVG', color: '#26a69a' },
  { key: 'ifvg', label: 'IFVG', color: '#7c6af7' },
  { key: 'bpr', label: 'BPR', color: '#f59e0b' },
  { key: 'liquidity', label: 'Liquidity', color: '#6b7280' },
  { key: 'sweeps', label: 'Sweeps', color: '#ec4899' },
  { key: 'killzones', label: 'Kill Zones', color: '#374151' },
  { key: 'po3', label: 'PO3/AMD', color: '#8b5cf6' },
  { key: 'turtle_s1', label: 'Turtle S1', color: '#22c55e' },
  { key: 'turtle_s2', label: 'Turtle S2', color: '#60a5fa' },
  { key: 'ma20', label: 'MA 20', color: '#f59e0b' },
  { key: 'ma50', label: 'MA 50', color: '#3b82f6' },
  { key: 'ma200', label: 'MA 200', color: '#ef4444' },
  { key: 'ema50', label: 'EMA 50', color: '#a855f7' },
  { key: 'vwap', label: 'VWAP', color: '#6b7280' },
  { key: 'volume', label: 'Volume', color: '#374151' },
];

export default function DashboardPage() {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [symbolInput, setSymbolInput] = useState('BTCUSDT');
  const [interval, setInterval] = useState('1h');
  const [startDate, setStartDate] = useState('2025-06-01');
  const [endDate, setEndDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [visibility, setVisibility] = useState<Visibility>({
    fvg: true,
    ifvg: false,
    bpr: true,
    liquidity: true,
    sweeps: true,
    killzones: true,
    po3: true,
    turtle_s1: false,
    turtle_s2: false,
    ma20: false,
    ma50: false,
    ma200: false,
    ema50: false,
    vwap: false,
    volume: true,
  });
  const [turtleData, setTurtleData] = useState<TurtleDonchianResponse | null>(null);

  const [candles, setCandles] = useState<Candle[]>([]);
  const [fvgs, setFvgs] = useState<FVG[]>([]);
  const [ifvgs, setIfvgs] = useState<IFVG[]>([]);
  const [bprs, setBprs] = useState<BPR[]>([]);
  const [liquidities, setLiquidities] = useState<LiquidityPool[]>([]);
  const [sweeps, setSweeps] = useState<Sweep[]>([]);
  const [killzones, setKillzones] = useState<KillZoneSpan[]>([]);
  const [po3s, setPo3s] = useState<PO3[]>([]);

  const [btMetrics, setBtMetrics] = useState<Metrics | null>(null);
  const [btTrades, setBtTrades] = useState<Trade[]>([]);
  const [btRunId, setBtRunId] = useState('');
  const [killZoneOnly, setKillZoneOnly] = useState(false);
  const [requireSweep, setRequireSweep] = useState(false);
  const [htfInterval, setHtfInterval] = useState('');
  const [htfBprs, setHtfBprs] = useState<BPR[]>([]);
  const [checklist, setChecklist] = useState<ChecklistResult | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([]);
  const [comparisonRuns, setComparisonRuns] = useState<[BacktestRun, BacktestRun] | null>(null);

  const [activeTab, setActiveTab] = useState<'chart' | 'journal' | 'macro'>('chart');

  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [stats, setStats] = useState('');
  const [liveMode, setLiveMode] = useState(false);

  // ── Auto-load actual data range on mount ─────────────────────
  useEffect(() => {
    fetchCandleRange(symbol, interval)
      .then((range) => {
        if (range) {
          setStartDate(range.start.slice(0, 10));
          setEndDate(range.end.slice(0, 10));
        }
      })
      .catch(() => undefined);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Live WebSocket stream ──────────────────────────────────────
  const { status: wsStatus, liveCandle, patternUpdate } = useKlineStream(symbol, interval, liveMode);

  // Merge live candle into candles array
  useEffect(() => {
    if (!liveCandle) return;
    setCandles((prev) => {
      if (prev.length === 0) return prev;
      const last = prev[prev.length - 1];
      const liveTime = liveCandle.open_time;
      if (last.open_time === liveTime) {
        // Update current candle in-place
        const updated = [...prev];
        updated[updated.length - 1] = {
          open_time: liveCandle.open_time,
          open: liveCandle.open,
          high: liveCandle.high,
          low: liveCandle.low,
          close: liveCandle.close,
          volume: liveCandle.volume,
        };
        return updated;
      }
      // New candle opened
      return [
        ...prev,
        {
          open_time: liveCandle.open_time,
          open: liveCandle.open,
          high: liveCandle.high,
          low: liveCandle.low,
          close: liveCandle.close,
          volume: liveCandle.volume,
        },
      ];
    });
  }, [liveCandle]);

  // Apply live pattern update (fires once per closed candle)
  useEffect(() => {
    if (!patternUpdate) return;
    setFvgs(patternUpdate.fvgs ?? []);
    setIfvgs(patternUpdate.ifvgs ?? []);
    setBprs(patternUpdate.bprs ?? []);
    setSweeps(patternUpdate.sweeps ?? []);
    setLiquidities(patternUpdate.liquidities ?? []);
    setKillzones(patternUpdate.killzones ?? []);
    setPo3s(patternUpdate.po3s ?? []);
    // Auto-refresh checklist on each closed candle in live mode
    fetchChecklist(symbol, interval, htfInterval || '1h')
      .then(setChecklist)
      .catch(() => undefined);
  }, [patternUpdate, symbol, interval, htfInterval]);

  // ── Helpers ───────────────────────────────────────────────────
  const parseErrorMsg = (e: unknown): string => {
    const raw = e instanceof Error ? e.message : String(e);
    try {
      const j = JSON.parse(raw) as { detail?: string };
      return j.detail ?? raw;
    } catch {
      return raw;
    }
  };

  // ── Handlers ──────────────────────────────────────────────────
  const handleSymbolChange = async (raw: string) => {
    const sym = raw.toUpperCase().trim();
    if (!sym || sym === symbol) return;
    setSymbol(sym);
    setSymbolInput(sym);
    setCandles([]);
    setBtTrades([]);
    setBtMetrics(null);
    setTurtleData(null);
    setChecklist(null);
    try {
      const range = await fetchCandleRange(sym, interval);
      if (range) {
        setStartDate(range.start.slice(0, 10));
        setEndDate(range.end.slice(0, 10));
      }
    } catch {
      // no data yet — user can ingest
    }
  };

  const handleIntervalChange = async (newInterval: string) => {
    setInterval(newInterval);
    setCandles([]); // clear stale series so live tick path isn't triggered before reload
    try {
      const range = await fetchCandleRange(symbol, newInterval);
      if (range) {
        setStartDate(range.start.slice(0, 10));
        setEndDate(range.end.slice(0, 10));
      }
    } catch {
      // silently ignore — user can set dates manually
    }
  };

  const handleLoad = async () => {
    setStatus('loading');
    setErrorMsg('');
    try {
      const start = startDate ? `${startDate}T00:00:00Z` : undefined;
      const end = endDate ? `${endDate}T23:59:59Z` : undefined;

      const t0 = performance.now();
      const turtleNeeded = visibility.turtle_s1 || visibility.turtle_s2;
      const [candleRes, patternRes, turtleRes] = await Promise.all([
        fetchCandles(symbol, interval, start, end),
        fetchPatterns(symbol, interval, start, end),
        turtleNeeded ? fetchTurtleDonchian(symbol, interval, start, end) : Promise.resolve(null),
      ]);
      setTurtleData(turtleRes);
      const elapsed = ((performance.now() - t0) / 1000).toFixed(2);

      setCandles(candleRes.candles ?? []);
      setFvgs(patternRes.fvgs ?? []);
      setIfvgs(patternRes.ifvgs ?? []);
      setBprs(patternRes.bprs ?? []);
      setLiquidities(patternRes.liquidities ?? []);
      setSweeps(patternRes.sweeps ?? []);
      setKillzones(patternRes.killzones ?? []);
      setPo3s(patternRes.po3s ?? []);

      const po3Count = (patternRes.po3s ?? []).length;
      setStats(
        `${candleRes.candles.length} candles | ${patternRes.fvgs.length} FVGs | ` +
          `${patternRes.bprs.length} BPRs | ${patternRes.liquidities.length} pools | ` +
          `${patternRes.sweeps.length} sweeps | ${po3Count} PO3 | ${elapsed}s`,
      );
      setStatus('idle');
    } catch (e) {
      setErrorMsg(parseErrorMsg(e));
      setStatus('error');
    }
  };

  const handleBacktest = async () => {
    setStatus('loading');
    setErrorMsg('');
    try {
      const start = startDate ? `${startDate}T00:00:00Z` : undefined;
      const end = endDate ? `${endDate}T23:59:59Z` : undefined;
      const result = await runBacktest(symbol, interval, start, end, killZoneOnly, requireSweep, htfInterval || undefined);
      setBtMetrics(result.metrics);
      setBtTrades(result.trades);
      setBtRunId(result.run_id);
      setHtfBprs(result.htf_bprs ?? []);
      setStats(
        `Backtest: ${result.metrics.total_trades} trades | ` +
          `WR ${(result.metrics.win_rate * 100).toFixed(1)}% | ` +
          `PF ${result.metrics.profit_factor === Infinity ? '∞' : result.metrics.profit_factor.toFixed(2)} | ` +
          `${result.metrics.total_pnl_r.toFixed(2)}R total`,
      );
      setStatus('idle');
    } catch (e) {
      setErrorMsg(parseErrorMsg(e));
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
      setErrorMsg(parseErrorMsg(e));
      setStatus('error');
    }
  };

  const storedToTrade = (st: StoredTrade): Trade => ({
    entry: {
      bpr: { type: st.direction === 'long' ? 'bull' : 'bear', top: st.tp, bottom: st.sl,
             fvg_old_time: st.entry_time, fvg_new_time: st.entry_time,
             created_time: st.entry_time, created_index: st.entry_index } as BPR,
      trigger_candle_index: st.entry_index,
      trigger_candle_time: st.entry_time,
      entry_index: st.entry_index,
      entry_time: st.entry_time,
      entry_price: st.entry_price,
      direction: st.direction,
    },
    sl: st.sl, tp: st.tp,
    exit_index: st.exit_index, exit_time: st.exit_time, exit_price: st.exit_price,
    status: st.status, pnl_r: st.pnl_r,
  });

  const handleLoadHistory = async () => {
    setStatus('loading');
    setErrorMsg('');
    try {
      const data = await fetchRuns();
      setRuns(data);
      setShowHistory(true);
      setStatus('idle');
    } catch (e) {
      setErrorMsg(parseErrorMsg(e));
      setStatus('error');
    }
  };

  const handleSelectRun = (runId: string) => {
    setSelectedRunIds((prev) => {
      if (prev.includes(runId)) return prev.filter((id) => id !== runId);
      if (prev.length >= 2) return [prev[1], runId];
      return [...prev, runId];
    });
    // Update comparison if 2 selected
    setComparisonRuns(null);
  };

  const handleViewRun = async (runId: string) => {
    setStatus('loading');
    setErrorMsg('');
    try {
      const detail = await fetchRunDetail(runId);
      setBtTrades(detail.trades.map(storedToTrade));
      setBtMetrics(null); // clear current metrics to signal we're viewing history
      setStatus('idle');
    } catch (e) {
      setErrorMsg(parseErrorMsg(e));
      setStatus('error');
    }
  };

  const handleCompare = () => {
    if (selectedRunIds.length < 2) return;
    const a = runs.find((r) => r.run_id === selectedRunIds[0]);
    const b = runs.find((r) => r.run_id === selectedRunIds[1]);
    if (a && b) setComparisonRuns([a, b]);
  };

  const handleChecklist = async () => {
    setStatus('loading');
    setErrorMsg('');
    try {
      const result = await fetchChecklist(symbol, interval, htfInterval || '1h');
      setChecklist(result);
      setStatus('idle');
    } catch (e) {
      setErrorMsg(parseErrorMsg(e));
      setStatus('error');
    }
  };

  const toggleVisibility = (key: keyof Visibility) => {
    setVisibility((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const maDistances = useMemo(() => {
    if (candles.length === 0) return null;
    const last = candles[candles.length - 1].close;

    const smaLast = (period: number) => {
      if (candles.length < period) return null;
      let sum = 0;
      for (let i = candles.length - period; i < candles.length; i++) sum += candles[i].close;
      return sum / period;
    };

    const emaLast = (period: number) => {
      if (candles.length < period) return null;
      const k = 2 / (period + 1);
      let val = 0;
      for (let i = 0; i < period; i++) val += candles[i].close;
      val /= period;
      for (let i = period; i < candles.length; i++) val = candles[i].close * k + val * (1 - k);
      return val;
    };

    const entries: { label: string; color: string; pct: number }[] = [];
    if (visibility.ma20)  { const v = smaLast(20);  if (v) entries.push({ label: 'MA20',  color: '#f59e0b', pct: (last - v) / v * 100 }); }
    if (visibility.ma50)  { const v = smaLast(50);  if (v) entries.push({ label: 'MA50',  color: '#3b82f6', pct: (last - v) / v * 100 }); }
    if (visibility.ma200) { const v = smaLast(200); if (v) entries.push({ label: 'MA200', color: '#ef4444', pct: (last - v) / v * 100 }); }
    if (visibility.ema50) { const v = emaLast(50); if (v) entries.push({ label: 'EMA50', color: '#a855f7', pct: (last - v) / v * 100 }); }

    if (visibility.vwap && candles.length > 0) {
      let cumTV = 0, cumVol = 0, currentDay = '';
      for (const c of candles) {
        const day = c.open_time.slice(0, 10);
        if (day !== currentDay) { cumTV = 0; cumVol = 0; currentDay = day; }
        const tp = (c.high + c.low + c.close) / 3;
        cumTV += tp * c.volume;
        cumVol += c.volume;
      }
      const v = cumTV / cumVol;
      entries.push({ label: 'VWAP', color: '#d1d4dc', pct: (last - v) / v * 100 });
    }

    return entries.length > 0 ? entries : null;
  }, [candles, visibility.ma20, visibility.ma50, visibility.ma200, visibility.ema50, visibility.vwap]);

  return (
    <main className="min-h-screen p-4" style={{ background: '#0d0f17' }}>
      <div className="flex items-center gap-4 mb-4">
        <h1 className="text-xl font-bold text-white">ICT Backtest Dashboard</h1>
        <div className="flex gap-1">
          {(['chart', 'journal', 'macro'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-1 rounded text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-[#2a2e39] text-white'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {tab === 'chart' ? 'Chart' : tab === 'journal' ? 'Journal' : 'Macro'}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'journal' && <JournalTab />}
      {activeTab === 'macro' && <MacroTab />}

      {activeTab === 'chart' && (<>
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mb-3">
        <datalist id="symbol-list">
          {['BTCUSDT','ETHUSDT','BNBUSDT','SOLUSDT','XRPUSDT','DOGEUSDT','ADAUSDT','AVAXUSDT','LINKUSDT','DOTUSDT'].map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
        <input
          list="symbol-list"
          value={symbolInput}
          onChange={(e) => setSymbolInput(e.target.value.toUpperCase())}
          onBlur={(e) => void handleSymbolChange(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') void handleSymbolChange(symbolInput); }}
          className="px-3 py-1.5 rounded bg-[#1e2130] text-white text-sm font-mono border border-[#2a2e39] w-32 uppercase"
          placeholder="BTCUSDT"
        />

        <select
          value={interval}
          onChange={(e) => void handleIntervalChange(e.target.value)}
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
          onClick={handleLoadHistory}
          disabled={status === 'loading'}
          className="px-4 py-1.5 rounded bg-[#2a1f3d] hover:bg-[#3a2f55] disabled:opacity-50 text-purple-300 text-sm border border-purple-800 transition-colors"
        >
          History
        </button>
        <button
          onClick={handleIngest}
          disabled={status === 'loading'}
          className="px-4 py-1.5 rounded bg-[#2a2e39] hover:bg-[#363c4e] disabled:opacity-50 text-gray-300 text-sm transition-colors"
        >
          Ingest Data
        </button>
        <button
          onClick={handleChecklist}
          disabled={status === 'loading'}
          className="px-4 py-1.5 rounded bg-[#1e2a3a] hover:bg-[#243347] disabled:opacity-50 text-cyan-400 text-sm font-semibold border border-cyan-800 transition-colors"
        >
          Checklist
        </button>

        {/* Live toggle */}
        <button
          onClick={() => setLiveMode((v) => !v)}
          className={`px-4 py-1.5 rounded text-sm font-semibold transition-colors border ${
            liveMode
              ? 'bg-green-700 hover:bg-green-600 text-white border-green-500'
              : 'bg-transparent text-gray-400 border-[#2a2e39] hover:border-green-700 hover:text-green-400'
          }`}
        >
          {liveMode ? '⬤ Live' : '○ Live'}
        </button>

        {liveMode && wsStatus !== 'disconnected' && (
          <span className={`text-xs font-mono ${WS_STATUS_STYLE[wsStatus] ?? ''}`}>
            {WS_STATUS_LABEL[wsStatus]}
          </span>
        )}

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

        <div className="flex items-center gap-1.5">
          <span className="text-xs text-gray-400">HTF:</span>
          <select
            value={htfInterval}
            onChange={(e) => setHtfInterval(e.target.value)}
            className="px-2 py-1 rounded bg-[#1e2130] text-white text-xs border border-[#2a2e39]"
          >
            <option value="">off</option>
            <option value="1h">1h</option>
            <option value="4h">4h</option>
            <option value="1d">1d</option>
          </select>
        </div>
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

      {/* MA distance panel */}
      {maDistances && (
        <div className="flex flex-wrap gap-3 mb-2">
          {maDistances.map(({ label, color, pct }) => (
            <span key={label} className="flex items-center gap-1 text-xs font-mono">
              <span style={{ color }}>{label}</span>
              <span className={pct >= 0 ? 'text-green-400' : 'text-red-400'}>
                {pct >= 0 ? '+' : ''}{pct.toFixed(2)}%
              </span>
            </span>
          ))}
        </div>
      )}

      {/* Chart */}
      <CandleChart
        candles={candles}
        fvgs={fvgs}
        ifvgs={ifvgs}
        bprs={bprs}
        liquidities={liquidities}
        sweeps={sweeps}
        killzones={killzones}
        po3s={po3s}
        htfBprs={htfBprs}
        turtleData={turtleData}
        visibility={visibility}
        trades={btTrades}
        liveMode={liveMode}
      />

      {/* Checklist */}
      {checklist && (
        <div className="mt-4">
          <ChecklistPanel result={checklist} />
        </div>
      )}

      {/* Backtest results */}
      {btMetrics && (
        <div className="mt-4 flex flex-col gap-3">
          <MetricsPanel metrics={btMetrics} runId={btRunId} />
          <TradesTable trades={btTrades} />
        </div>
      )}

      {/* Run history */}
      {showHistory && (
        <div className="mt-4 flex flex-col gap-3">
          {selectedRunIds.length === 2 && (
            <div className="flex justify-end">
              <button
                onClick={handleCompare}
                className="px-4 py-1.5 rounded bg-purple-700 hover:bg-purple-600 text-white text-sm font-semibold transition-colors"
              >
                Compare Selected ({selectedRunIds.length}/2)
              </button>
            </div>
          )}
          <RunHistory
            runs={runs}
            selectedIds={selectedRunIds}
            onSelect={handleSelectRun}
            onView={handleViewRun}
          />
          {comparisonRuns && (
            <RunComparison runA={comparisonRuns[0]} runB={comparisonRuns[1]} />
          )}
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
      </>)}
    </main>
  );
}
