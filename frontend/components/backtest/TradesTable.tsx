'use client';

import type { Trade } from '@/lib/types';

interface Props {
  trades: Trade[];
}

const STATUS_STYLE: Record<Trade['status'], string> = {
  closed_win: 'text-green-400',
  closed_loss: 'text-red-400',
  closed_timeout: 'text-yellow-400',
};

const STATUS_LABEL: Record<Trade['status'], string> = {
  closed_win: 'WIN',
  closed_loss: 'LOSS',
  closed_timeout: 'TIMEOUT',
};

function fmtTime(iso: string): string {
  return iso.replace('T', ' ').slice(0, 16);
}

function fmtPrice(n: number): string {
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function TradesTable({ trades }: Props) {
  if (trades.length === 0) return null;

  return (
    <div className="rounded-lg border border-[#2a2e39] overflow-hidden">
      <div className="overflow-x-auto max-h-64">
        <table className="w-full text-xs font-mono text-gray-300">
          <thead className="bg-[#1a1d2e] text-gray-500 sticky top-0">
            <tr>
              <th className="px-2 py-1.5 text-left">#</th>
              <th className="px-2 py-1.5 text-left">Dir</th>
              <th className="px-2 py-1.5 text-left">Entry Time</th>
              <th className="px-2 py-1.5 text-right">Entry</th>
              <th className="px-2 py-1.5 text-right">SL</th>
              <th className="px-2 py-1.5 text-right">TP</th>
              <th className="px-2 py-1.5 text-left">Exit Time</th>
              <th className="px-2 py-1.5 text-right">Exit</th>
              <th className="px-2 py-1.5 text-right">PnL (R)</th>
              <th className="px-2 py-1.5 text-left">Status</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t, i) => (
              <tr
                key={i}
                className="border-t border-[#1e2130] hover:bg-[#1a1d2e] transition-colors"
              >
                <td className="px-2 py-1 text-gray-600">{i + 1}</td>
                <td className={`px-2 py-1 ${t.entry.direction === 'long' ? 'text-green-400' : 'text-red-400'}`}>
                  {t.entry.direction.toUpperCase()}
                </td>
                <td className="px-2 py-1">{fmtTime(t.entry.entry_time)}</td>
                <td className="px-2 py-1 text-right">{fmtPrice(t.entry.entry_price)}</td>
                <td className="px-2 py-1 text-right text-red-300">{fmtPrice(t.sl)}</td>
                <td className="px-2 py-1 text-right text-green-300">{fmtPrice(t.tp)}</td>
                <td className="px-2 py-1">{fmtTime(t.exit_time)}</td>
                <td className="px-2 py-1 text-right">{fmtPrice(t.exit_price)}</td>
                <td className={`px-2 py-1 text-right ${t.pnl_r >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {t.pnl_r >= 0 ? '+' : ''}{t.pnl_r.toFixed(2)}R
                </td>
                <td className={`px-2 py-1 ${STATUS_STYLE[t.status]}`}>
                  {STATUS_LABEL[t.status]}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
