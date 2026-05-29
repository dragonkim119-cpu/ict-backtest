'use client';

import type { JournalEntry } from '@/lib/types';

interface Props {
  entries: JournalEntry[];
  selectedId: number | null;
  onSelect: (entry: JournalEntry) => void;
  onDelete: (id: number) => void;
}

function fmt(n: number | null, digits = 2): string {
  if (n === null || n === undefined) return '—';
  return n.toFixed(digits);
}

function fmtDate(iso: string): string {
  return iso.slice(0, 16).replace('T', ' ');
}

export default function JournalTable({ entries, selectedId, onSelect, onDelete }: Props) {
  if (entries.length === 0) {
    return (
      <div className="rounded-lg border border-[#2a2e39] bg-[#131722] p-6 text-center text-xs text-gray-500">
        No journal entries yet. Click "+ New Entry" to add one.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-[#2a2e39] bg-[#131722] overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[#2a2e39] text-gray-500">
              <th className="px-3 py-2 text-left">Entry Time</th>
              <th className="px-3 py-2 text-left">Dir</th>
              <th className="px-3 py-2 text-left">TF</th>
              <th className="px-3 py-2 text-right">Entry</th>
              <th className="px-3 py-2 text-right">Exit</th>
              <th className="px-3 py-2 text-right">PnL R</th>
              <th className="px-3 py-2 text-right">RR</th>
              <th className="px-3 py-2 text-left">Tags</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => {
              const isSelected = e.id === selectedId;
              const isWin = e.result_pnl !== null && e.result_pnl > 0;
              const isLoss = e.result_pnl !== null && e.result_pnl <= 0;
              return (
                <tr
                  key={e.id}
                  onClick={() => onSelect(e)}
                  className={`border-b border-[#1e2130] cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-blue-900/30 hover:bg-blue-900/40'
                      : 'hover:bg-[#1e2130]'
                  }`}
                >
                  <td className="px-3 py-1.5 text-gray-400 font-mono whitespace-nowrap">
                    {fmtDate(e.entry_time)}
                  </td>
                  <td className="px-3 py-1.5 font-semibold">
                    <span className={e.direction === 'long' ? 'text-green-400' : 'text-red-400'}>
                      {e.direction === 'long' ? '▲' : '▼'} {e.direction}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-gray-300 font-mono">{e.interval}</td>
                  <td className="px-3 py-1.5 text-right text-white font-mono">
                    {e.entry_price.toLocaleString()}
                  </td>
                  <td className="px-3 py-1.5 text-right text-gray-400 font-mono">
                    {e.exit_price !== null ? e.exit_price.toLocaleString() : '—'}
                  </td>
                  <td className={`px-3 py-1.5 text-right font-semibold ${
                    isWin ? 'text-green-400' : isLoss ? 'text-red-400' : 'text-gray-500'
                  }`}>
                    {e.result_pnl !== null ? `${fmt(e.result_pnl)}R` : '—'}
                  </td>
                  <td className="px-3 py-1.5 text-right text-gray-400">
                    {fmt(e.rr)}
                  </td>
                  <td className="px-3 py-1.5 max-w-[120px]">
                    <div className="flex flex-wrap gap-1">
                      {e.tags.map((t) => (
                        <span key={t} className="px-1.5 py-0.5 rounded bg-[#2a2e39] text-gray-300 text-[10px]">
                          {t}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-3 py-1.5">
                    <button
                      onClick={(ev) => { ev.stopPropagation(); onDelete(e.id); }}
                      className="px-2 py-0.5 rounded text-xs bg-[#2a2e39] hover:bg-red-900/50 hover:text-red-400 text-gray-500 transition-colors"
                    >
                      ✕
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
