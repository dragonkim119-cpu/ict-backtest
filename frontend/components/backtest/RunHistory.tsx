'use client';

import type { BacktestRun } from '@/lib/types';

interface Props {
  runs: BacktestRun[];
  selectedIds: string[];
  onSelect: (runId: string) => void;
  onView: (runId: string) => void;
}

function fmt(n: number | null, digits = 2) {
  if (n === null || n === undefined) return '—';
  return n.toFixed(digits);
}

function pf(v: number | null) {
  if (v === null || v === undefined) return '—';
  if (!isFinite(v)) return '∞';
  return v.toFixed(2);
}

function parseParams(json: string) {
  try {
    const p = JSON.parse(json);
    const parts: string[] = [];
    if (p.htf_interval) parts.push(`HTF:${p.htf_interval}`);
    return parts.join(' ') || '—';
  } catch {
    return '—';
  }
}

export default function RunHistory({ runs, selectedIds, onSelect, onView }: Props) {
  if (runs.length === 0) {
    return (
      <div className="rounded-lg border border-[#2a2e39] bg-[#131722] p-4 text-xs text-gray-500">
        No backtest runs yet.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-[#2a2e39] bg-[#131722] overflow-hidden">
      <div className="px-4 py-2 border-b border-[#2a2e39] flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">Run History</h2>
        <span className="text-xs text-gray-500">
          {selectedIds.length}/2 selected — click rows to compare
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[#2a2e39] text-gray-500">
              <th className="px-3 py-2 text-left">Date</th>
              <th className="px-3 py-2 text-left">TF</th>
              <th className="px-3 py-2 text-left">Params</th>
              <th className="px-3 py-2 text-right">Trades</th>
              <th className="px-3 py-2 text-right">WR%</th>
              <th className="px-3 py-2 text-right">PF</th>
              <th className="px-3 py-2 text-right">PnL R</th>
              <th className="px-3 py-2 text-right">MDD</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => {
              const selected = selectedIds.includes(r.run_id);
              return (
                <tr
                  key={r.run_id}
                  onClick={() => onSelect(r.run_id)}
                  className={`border-b border-[#1e2130] cursor-pointer transition-colors ${
                    selected
                      ? 'bg-purple-900/30 hover:bg-purple-900/40'
                      : 'hover:bg-[#1e2130]'
                  }`}
                >
                  <td className="px-3 py-1.5 text-gray-400 font-mono">
                    {r.created_at.slice(0, 16).replace('T', ' ')}
                  </td>
                  <td className="px-3 py-1.5 text-white font-mono">{r.interval}</td>
                  <td className="px-3 py-1.5 text-gray-400">{parseParams(r.params_json)}</td>
                  <td className="px-3 py-1.5 text-right text-white">{r.total_trades}</td>
                  <td className="px-3 py-1.5 text-right text-white">
                    {fmt(r.win_rate * 100, 1)}%
                  </td>
                  <td className="px-3 py-1.5 text-right text-white">{pf(r.profit_factor)}</td>
                  <td
                    className={`px-3 py-1.5 text-right font-medium ${
                      r.total_pnl_r >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}
                  >
                    {fmt(r.total_pnl_r)}R
                  </td>
                  <td className="px-3 py-1.5 text-right text-red-400">
                    {fmt(r.max_drawdown_r)}
                  </td>
                  <td className="px-3 py-1.5">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onView(r.run_id);
                      }}
                      className="px-2 py-0.5 rounded text-xs bg-[#2a2e39] hover:bg-[#363c4e] text-gray-300 transition-colors"
                    >
                      View
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
