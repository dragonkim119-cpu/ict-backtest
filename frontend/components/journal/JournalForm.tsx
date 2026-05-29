'use client';

import { useState } from 'react';

import type { JournalEntry, JournalEntryCreate } from '@/lib/types';

const INTERVALS = ['1m', '5m', '15m', '1h', '4h', '1d'];

interface Props {
  onCreated: (entry: JournalEntry) => void;
  onCancel: () => void;
  onCreate: (data: JournalEntryCreate) => Promise<JournalEntry>;
}

function toLocalDatetime(iso: string) {
  // Convert ISO to datetime-local input value (YYYY-MM-DDTHH:mm)
  return iso.slice(0, 16);
}

function toIso(local: string) {
  return local ? `${local}:00Z` : '';
}

export default function JournalForm({ onCreated, onCancel, onCreate }: Props) {
  const now = new Date();
  const localNow = toLocalDatetime(now.toISOString());

  const [direction, setDirection] = useState<'long' | 'short'>('long');
  const [interval, setInterval] = useState('1h');
  const [entryTime, setEntryTime] = useState(localNow);
  const [entryPrice, setEntryPrice] = useState('');
  const [exitTime, setExitTime] = useState('');
  const [exitPrice, setExitPrice] = useState('');
  const [sl, setSl] = useState('');
  const [tp, setTp] = useState('');
  const [resultPnl, setResultPnl] = useState('');
  const [rr, setRr] = useState('');
  const [notes, setNotes] = useState('');
  const [tags, setTags] = useState('');
  const [runId, setRunId] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!entryPrice) { setError('Entry price required'); return; }
    setError('');
    setSaving(true);
    try {
      const data: JournalEntryCreate = {
        symbol: 'BTCUSDT',
        interval,
        direction,
        entry_time: toIso(entryTime),
        entry_price: parseFloat(entryPrice),
        exit_time: exitTime ? toIso(exitTime) : null,
        exit_price: exitPrice ? parseFloat(exitPrice) : null,
        sl: sl ? parseFloat(sl) : null,
        tp: tp ? parseFloat(tp) : null,
        result_pnl: resultPnl ? parseFloat(resultPnl) : null,
        rr: rr ? parseFloat(rr) : null,
        notes,
        tags: tags ? tags.split(',').map((t) => t.trim()).filter(Boolean) : [],
        run_id: runId || null,
      };
      const created = await onCreate(data);
      onCreated(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const inputCls = 'w-full px-2 py-1 rounded bg-[#1e2130] text-white text-xs border border-[#2a2e39] focus:outline-none focus:border-blue-500';
  const labelCls = 'block text-xs text-gray-400 mb-0.5';

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">New Journal Entry</h3>
        <button type="button" onClick={onCancel} className="text-gray-500 hover:text-white text-xs">✕</button>
      </div>

      {/* Direction + Interval */}
      <div className="flex gap-3">
        <div className="flex-1">
          <label className={labelCls}>Direction</label>
          <div className="flex gap-1.5">
            {(['long', 'short'] as const).map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => setDirection(d)}
                className={`flex-1 py-1 rounded text-xs font-semibold transition-colors ${
                  direction === d
                    ? d === 'long' ? 'bg-green-700 text-white' : 'bg-red-700 text-white'
                    : 'bg-[#2a2e39] text-gray-400 hover:text-white'
                }`}
              >
                {d === 'long' ? '▲ Long' : '▼ Short'}
              </button>
            ))}
          </div>
        </div>
        <div className="w-24">
          <label className={labelCls}>Interval</label>
          <select value={interval} onChange={(e) => setInterval(e.target.value)} className={inputCls}>
            {INTERVALS.map((i) => <option key={i} value={i}>{i}</option>)}
          </select>
        </div>
      </div>

      {/* Entry */}
      <div className="flex gap-3">
        <div className="flex-1">
          <label className={labelCls}>Entry Time</label>
          <input type="datetime-local" value={entryTime} onChange={(e) => setEntryTime(e.target.value)} className={inputCls} />
        </div>
        <div className="w-32">
          <label className={labelCls}>Entry Price *</label>
          <input type="number" step="any" placeholder="65000" value={entryPrice} onChange={(e) => setEntryPrice(e.target.value)} className={inputCls} />
        </div>
      </div>

      {/* SL / TP */}
      <div className="flex gap-3">
        <div className="flex-1">
          <label className={labelCls}>Stop Loss</label>
          <input type="number" step="any" placeholder="64000" value={sl} onChange={(e) => setSl(e.target.value)} className={inputCls} />
        </div>
        <div className="flex-1">
          <label className={labelCls}>Take Profit</label>
          <input type="number" step="any" placeholder="68000" value={tp} onChange={(e) => setTp(e.target.value)} className={inputCls} />
        </div>
      </div>

      {/* Exit */}
      <div className="flex gap-3">
        <div className="flex-1">
          <label className={labelCls}>Exit Time</label>
          <input type="datetime-local" value={exitTime} onChange={(e) => setExitTime(e.target.value)} className={inputCls} />
        </div>
        <div className="w-32">
          <label className={labelCls}>Exit Price</label>
          <input type="number" step="any" value={exitPrice} onChange={(e) => setExitPrice(e.target.value)} className={inputCls} />
        </div>
      </div>

      {/* Result */}
      <div className="flex gap-3">
        <div className="flex-1">
          <label className={labelCls}>Result PnL (R)</label>
          <input type="number" step="any" placeholder="2.5" value={resultPnl} onChange={(e) => setResultPnl(e.target.value)} className={inputCls} />
        </div>
        <div className="flex-1">
          <label className={labelCls}>Actual RR</label>
          <input type="number" step="any" placeholder="2.5" value={rr} onChange={(e) => setRr(e.target.value)} className={inputCls} />
        </div>
      </div>

      {/* Notes / Tags */}
      <div>
        <label className={labelCls}>Notes</label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          placeholder="Setup notes, emotions, mistakes…"
          className={`${inputCls} resize-none`}
        />
      </div>
      <div className="flex gap-3">
        <div className="flex-1">
          <label className={labelCls}>Tags (comma-separated)</label>
          <input type="text" placeholder="bpr, sweep, london" value={tags} onChange={(e) => setTags(e.target.value)} className={inputCls} />
        </div>
        <div className="flex-1">
          <label className={labelCls}>Backtest Run ID</label>
          <input type="text" placeholder="optional" value={runId} onChange={(e) => setRunId(e.target.value)} className={inputCls} />
        </div>
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      <button
        type="submit"
        disabled={saving}
        className="px-4 py-1.5 rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold transition-colors"
      >
        {saving ? 'Saving…' : 'Save Entry'}
      </button>
    </form>
  );
}
