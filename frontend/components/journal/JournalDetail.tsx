'use client';

import { useEffect, useState } from 'react';

import type { BacktestRun, JournalCompareResult, JournalEntry, JournalEntryUpdate } from '@/lib/types';

interface Props {
  entry: JournalEntry;
  onClose: () => void;
  onUpdate: (update: JournalEntryUpdate) => Promise<JournalEntry>;
  onCompare: (id: number) => Promise<JournalCompareResult>;
}

function fmt(n: number | null, digits = 2): string {
  if (n === null || n === undefined) return '—';
  return n.toFixed(digits);
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  return iso.slice(0, 16).replace('T', ' ');
}

function pf(v: number | null): string {
  if (v === null || v === undefined) return '—';
  if (!isFinite(v)) return '∞';
  return v.toFixed(2);
}

function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-[#1e2130] rounded p-2 flex flex-col gap-0.5">
      <span className="text-[10px] text-gray-500">{label}</span>
      <span className={`text-sm font-semibold ${color ?? 'text-white'}`}>{value}</span>
    </div>
  );
}

function RunComparePanel({ run }: { run: BacktestRun }) {
  return (
    <div className="mt-3">
      <h4 className="text-xs text-gray-400 mb-2">Linked Backtest Run</h4>
      <div className="text-[10px] text-gray-500 font-mono mb-2 truncate">{run.run_id}</div>
      <div className="grid grid-cols-2 gap-1.5">
        <MetricCard label="Trades" value={String(run.total_trades)} />
        <MetricCard
          label="Win Rate"
          value={`${(run.win_rate * 100).toFixed(1)}%`}
          color={run.win_rate >= 0.5 ? 'text-green-400' : 'text-red-400'}
        />
        <MetricCard label="Profit Factor" value={pf(run.profit_factor)} />
        <MetricCard
          label="Total PnL R"
          value={`${fmt(run.total_pnl_r)}R`}
          color={run.total_pnl_r >= 0 ? 'text-green-400' : 'text-red-400'}
        />
        <MetricCard label="Max DD" value={`${fmt(run.max_drawdown_r)}R`} color="text-red-400" />
        <MetricCard label="Interval" value={run.interval} />
      </div>
    </div>
  );
}

export default function JournalDetail({ entry, onClose, onUpdate, onCompare }: Props) {
  const [editing, setEditing] = useState(false);
  const [compareResult, setCompareResult] = useState<JournalCompareResult | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // Edit fields
  const [exitTime, setExitTime] = useState(entry.exit_time?.slice(0, 16) ?? '');
  const [exitPrice, setExitPrice] = useState(entry.exit_price !== null ? String(entry.exit_price) : '');
  const [resultPnl, setResultPnl] = useState(entry.result_pnl !== null ? String(entry.result_pnl) : '');
  const [rr, setRr] = useState(entry.rr !== null ? String(entry.rr) : '');
  const [notes, setNotes] = useState(entry.notes);
  const [tags, setTags] = useState(entry.tags.join(', '));
  const [runId, setRunId] = useState(entry.run_id ?? '');

  useEffect(() => {
    setEditing(false);
    setCompareResult(null);
    setExitTime(entry.exit_time?.slice(0, 16) ?? '');
    setExitPrice(entry.exit_price !== null ? String(entry.exit_price) : '');
    setResultPnl(entry.result_pnl !== null ? String(entry.result_pnl) : '');
    setRr(entry.rr !== null ? String(entry.rr) : '');
    setNotes(entry.notes);
    setTags(entry.tags.join(', '));
    setRunId(entry.run_id ?? '');
  }, [entry.id]);

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const update: JournalEntryUpdate = {
        exit_time: exitTime ? `${exitTime}:00Z` : null,
        exit_price: exitPrice ? parseFloat(exitPrice) : null,
        result_pnl: resultPnl ? parseFloat(resultPnl) : null,
        rr: rr ? parseFloat(rr) : null,
        notes: notes || null,
        tags: tags ? tags.split(',').map((t) => t.trim()).filter(Boolean) : [],
        run_id: runId || null,
      };
      await onUpdate(update);
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleCompare = async () => {
    setCompareLoading(true);
    try {
      const result = await onCompare(entry.id);
      setCompareResult(result);
    } catch {
      // silently ignore
    } finally {
      setCompareLoading(false);
    }
  };

  const inputCls = 'w-full px-2 py-1 rounded bg-[#131722] text-white text-xs border border-[#2a2e39] focus:outline-none focus:border-blue-500';
  const rowCls = 'flex justify-between items-center py-1 border-b border-[#1e2130]';
  const keyStyle = 'text-xs text-gray-500';
  const valStyle = 'text-xs text-white font-mono';

  const isWin = entry.result_pnl !== null && entry.result_pnl > 0;
  const isLoss = entry.result_pnl !== null && entry.result_pnl <= 0;

  return (
    <div className="flex flex-col gap-3 h-full overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-bold ${entry.direction === 'long' ? 'text-green-400' : 'text-red-400'}`}>
            {entry.direction === 'long' ? '▲ LONG' : '▼ SHORT'}
          </span>
          <span className="text-xs text-gray-400 font-mono">{entry.interval}</span>
        </div>
        <div className="flex items-center gap-2">
          {!editing && (
            <button
              onClick={() => setEditing(true)}
              className="px-2 py-0.5 rounded text-xs bg-[#2a2e39] hover:bg-[#363c4e] text-gray-300"
            >
              Edit
            </button>
          )}
          <button onClick={onClose} className="text-gray-500 hover:text-white text-xs">✕</button>
        </div>
      </div>

      {!editing ? (
        <>
          {/* Detail rows */}
          <div className="rounded bg-[#131722] border border-[#2a2e39] px-3 py-1">
            <div className={rowCls}><span className={keyStyle}>Entry Time</span><span className={valStyle}>{fmtDate(entry.entry_time)}</span></div>
            <div className={rowCls}><span className={keyStyle}>Entry Price</span><span className={valStyle}>{entry.entry_price.toLocaleString()}</span></div>
            <div className={rowCls}><span className={keyStyle}>Stop Loss</span><span className={valStyle}>{entry.sl !== null ? entry.sl.toLocaleString() : '—'}</span></div>
            <div className={rowCls}><span className={keyStyle}>Take Profit</span><span className={valStyle}>{entry.tp !== null ? entry.tp.toLocaleString() : '—'}</span></div>
            <div className={rowCls}><span className={keyStyle}>Exit Time</span><span className={valStyle}>{fmtDate(entry.exit_time)}</span></div>
            <div className={rowCls}><span className={keyStyle}>Exit Price</span><span className={valStyle}>{entry.exit_price !== null ? entry.exit_price.toLocaleString() : '—'}</span></div>
            <div className={rowCls}>
              <span className={keyStyle}>Result PnL</span>
              <span className={`text-xs font-semibold font-mono ${isWin ? 'text-green-400' : isLoss ? 'text-red-400' : 'text-gray-500'}`}>
                {entry.result_pnl !== null ? `${fmt(entry.result_pnl)}R` : '—'}
              </span>
            </div>
            <div className={rowCls}><span className={keyStyle}>RR</span><span className={valStyle}>{fmt(entry.rr)}</span></div>
            {entry.run_id && (
              <div className="flex justify-between items-center py-1">
                <span className={keyStyle}>Run ID</span>
                <span className="text-[10px] text-blue-400 font-mono truncate max-w-[140px]">{entry.run_id}</span>
              </div>
            )}
          </div>

          {/* Notes */}
          {entry.notes && (
            <div className="rounded bg-[#131722] border border-[#2a2e39] px-3 py-2">
              <p className="text-xs text-gray-500 mb-1">Notes</p>
              <p className="text-xs text-gray-300 whitespace-pre-wrap">{entry.notes}</p>
            </div>
          )}

          {/* Tags */}
          {entry.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {entry.tags.map((t) => (
                <span key={t} className="px-2 py-0.5 rounded bg-[#2a2e39] text-gray-300 text-[10px]">{t}</span>
              ))}
            </div>
          )}

          {/* Compare button */}
          {entry.run_id && !compareResult && (
            <button
              onClick={handleCompare}
              disabled={compareLoading}
              className="px-3 py-1.5 rounded bg-[#1e2a3a] hover:bg-[#243347] disabled:opacity-50 text-cyan-400 text-xs font-semibold border border-cyan-800 transition-colors"
            >
              {compareLoading ? 'Loading…' : 'Compare with Backtest Run'}
            </button>
          )}

          {/* Compare result */}
          {compareResult?.run && <RunComparePanel run={compareResult.run} />}
          {compareResult && !compareResult.run && (
            <p className="text-xs text-gray-500">Linked backtest run not found in DB.</p>
          )}
        </>
      ) : (
        /* Edit mode */
        <div className="flex flex-col gap-2">
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="block text-[10px] text-gray-500 mb-0.5">Exit Time</label>
              <input type="datetime-local" value={exitTime} onChange={(e) => setExitTime(e.target.value)} className={inputCls} />
            </div>
            <div className="flex-1">
              <label className="block text-[10px] text-gray-500 mb-0.5">Exit Price</label>
              <input type="number" step="any" value={exitPrice} onChange={(e) => setExitPrice(e.target.value)} className={inputCls} />
            </div>
          </div>
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="block text-[10px] text-gray-500 mb-0.5">Result PnL (R)</label>
              <input type="number" step="any" value={resultPnl} onChange={(e) => setResultPnl(e.target.value)} className={inputCls} />
            </div>
            <div className="flex-1">
              <label className="block text-[10px] text-gray-500 mb-0.5">Actual RR</label>
              <input type="number" step="any" value={rr} onChange={(e) => setRr(e.target.value)} className={inputCls} />
            </div>
          </div>
          <div>
            <label className="block text-[10px] text-gray-500 mb-0.5">Notes</label>
            <textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} className={`${inputCls} resize-none`} />
          </div>
          <div>
            <label className="block text-[10px] text-gray-500 mb-0.5">Tags</label>
            <input type="text" value={tags} onChange={(e) => setTags(e.target.value)} className={inputCls} />
          </div>
          <div>
            <label className="block text-[10px] text-gray-500 mb-0.5">Backtest Run ID</label>
            <input type="text" value={runId} onChange={(e) => setRunId(e.target.value)} className={inputCls} />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex-1 py-1.5 rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold"
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button
              onClick={() => setEditing(false)}
              className="flex-1 py-1.5 rounded bg-[#2a2e39] hover:bg-[#363c4e] text-gray-300 text-xs"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
