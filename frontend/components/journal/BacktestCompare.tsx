'use client';

import type { JournalVsBacktest } from '@/lib/types';

interface Props {
  data: JournalVsBacktest;
}

function pct(n: number | null) {
  if (n === null || n === undefined) return '—';
  return `${(n * 100).toFixed(1)}%`;
}

function fmt(n: number | null, digits = 2) {
  if (n === null || n === undefined) return '—';
  if (!isFinite(n)) return '∞';
  return n.toFixed(digits);
}

function CompareRow({
  label,
  journal,
  backtest,
  journalColor,
  backtestColor,
}: {
  label: string;
  journal: string;
  backtest: string;
  journalColor?: string;
  backtestColor?: string;
}) {
  return (
    <tr className="border-b border-[#1e2130]">
      <td className="px-3 py-2 text-xs text-gray-500">{label}</td>
      <td className={`px-3 py-2 text-xs font-semibold text-center ${journalColor ?? 'text-white'}`}>
        {journal}
      </td>
      <td className={`px-3 py-2 text-xs font-semibold text-center ${backtestColor ?? 'text-white'}`}>
        {backtest}
      </td>
    </tr>
  );
}

export default function BacktestCompare({ data }: Props) {
  const { journal, backtest } = data;

  const jWRColor = journal.win_rate >= 0.5 ? 'text-green-400' : 'text-red-400';
  const bWRColor =
    backtest.avg_win_rate !== null
      ? backtest.avg_win_rate >= 0.5
        ? 'text-green-400'
        : 'text-red-400'
      : 'text-gray-500';
  const jPnlColor = journal.total_pnl_r >= 0 ? 'text-green-400' : 'text-red-400';
  const bPnlColor =
    backtest.avg_total_pnl_r !== null
      ? backtest.avg_total_pnl_r >= 0
        ? 'text-green-400'
        : 'text-red-400'
      : 'text-gray-500';

  return (
    <div className="rounded-lg border border-[#2a2e39] bg-[#131722] overflow-hidden">
      <div className="px-4 py-2 border-b border-[#2a2e39]">
        <h3 className="text-sm font-semibold text-white">Real vs Backtest</h3>
        <p className="text-[10px] text-gray-500 mt-0.5">
          Journal: {journal.closed_total} closed trades · Backtest: {backtest.total_runs} runs (averages)
        </p>
      </div>
      <table className="w-full">
        <thead>
          <tr className="border-b border-[#2a2e39]">
            <th className="px-3 py-2 text-xs text-gray-500 text-left">Metric</th>
            <th className="px-3 py-2 text-xs text-blue-400 text-center">Journal (Real)</th>
            <th className="px-3 py-2 text-xs text-purple-400 text-center">Backtest (Avg)</th>
          </tr>
        </thead>
        <tbody>
          <CompareRow
            label="Win Rate"
            journal={pct(journal.win_rate)}
            backtest={pct(backtest.avg_win_rate)}
            journalColor={jWRColor}
            backtestColor={bWRColor}
          />
          <CompareRow
            label="Avg RR"
            journal={fmt(journal.avg_rr)}
            backtest="—"
          />
          <CompareRow
            label="Profit Factor"
            journal="—"
            backtest={fmt(backtest.avg_profit_factor)}
          />
          <CompareRow
            label="Total / Avg PnL R"
            journal={`${journal.total_pnl_r >= 0 ? '+' : ''}${fmt(journal.total_pnl_r)}R`}
            backtest={backtest.avg_total_pnl_r !== null ? `${backtest.avg_total_pnl_r >= 0 ? '+' : ''}${fmt(backtest.avg_total_pnl_r)}R` : '—'}
            journalColor={jPnlColor}
            backtestColor={bPnlColor}
          />
          <CompareRow
            label="Trades / Runs"
            journal={String(journal.closed_total)}
            backtest={String(backtest.total_runs)}
          />
        </tbody>
      </table>

      {journal.closed_total === 0 && (
        <p className="px-4 py-3 text-xs text-gray-500">
          Add closed trades (with result_pnl) to journal to see real vs backtest comparison.
        </p>
      )}
    </div>
  );
}
