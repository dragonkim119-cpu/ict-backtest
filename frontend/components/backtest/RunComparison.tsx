'use client';

import type { BacktestRun } from '@/lib/types';

interface Props {
  runA: BacktestRun;
  runB: BacktestRun;
}

type MetricDef = {
  label: string;
  key: keyof BacktestRun;
  format: (v: number | null) => string;
  higherIsBetter: boolean;
};

const METRICS: MetricDef[] = [
  { label: 'Total Trades', key: 'total_trades', format: (v) => String(v ?? '—'), higherIsBetter: true },
  { label: 'Win Rate', key: 'win_rate', format: (v) => (v !== null ? `${(v * 100).toFixed(1)}%` : '—'), higherIsBetter: true },
  { label: 'Profit Factor', key: 'profit_factor', format: (v) => (v === null ? '—' : !isFinite(v) ? '∞' : v.toFixed(2)), higherIsBetter: true },
  { label: 'Expectancy', key: 'expectancy', format: (v) => (v !== null ? `${v.toFixed(3)}R` : '—'), higherIsBetter: true },
  { label: 'Total PnL', key: 'total_pnl_r', format: (v) => (v !== null ? `${v.toFixed(2)}R` : '—'), higherIsBetter: true },
  { label: 'Max Drawdown', key: 'max_drawdown_r', format: (v) => (v !== null ? `${v.toFixed(2)}R` : '—'), higherIsBetter: false },
  { label: 'Max Consec. Losses', key: 'max_consecutive_losses', format: (v) => String(v ?? '—'), higherIsBetter: false },
  { label: 'Wins', key: 'wins', format: (v) => String(v ?? '—'), higherIsBetter: true },
  { label: 'Losses', key: 'losses', format: (v) => String(v ?? '—'), higherIsBetter: false },
];

function cellColor(a: number | null, b: number | null, higherIsBetter: boolean, side: 'a' | 'b') {
  if (a === null || b === null || a === b) return 'text-white';
  const aWins = higherIsBetter ? a > b : a < b;
  if (side === 'a') return aWins ? 'text-green-400' : 'text-red-400';
  return aWins ? 'text-red-400' : 'text-green-400';
}

function parseParams(json: string): Record<string, string> {
  try {
    return JSON.parse(json);
  } catch {
    return {};
  }
}

function runLabel(r: BacktestRun) {
  return `${r.interval} · ${r.created_at.slice(0, 16).replace('T', ' ')}`;
}

export default function RunComparison({ runA, runB }: Props) {
  const paramsA = parseParams(runA.params_json);
  const paramsB = parseParams(runB.params_json);

  const paramKeys = Array.from(
    new Set([...Object.keys(paramsA), ...Object.keys(paramsB)]).values(),
  ).filter((k) => k !== 'symbol');

  return (
    <div className="rounded-lg border border-[#2a2e39] bg-[#131722] overflow-hidden">
      <div className="px-4 py-2 border-b border-[#2a2e39]">
        <h2 className="text-sm font-semibold text-white">Run Comparison</h2>
      </div>

      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-[#2a2e39] text-gray-500">
            <th className="px-4 py-2 text-left w-40">Metric</th>
            <th className="px-4 py-2 text-right text-purple-300">{runLabel(runA)}</th>
            <th className="px-4 py-2 text-right text-cyan-300">{runLabel(runB)}</th>
          </tr>
        </thead>
        <tbody>
          {/* Params section */}
          <tr className="border-b border-[#1e2130] bg-[#0d0f17]">
            <td colSpan={3} className="px-4 py-1.5 text-gray-500 font-semibold uppercase tracking-wide text-[10px]">
              Parameters
            </td>
          </tr>
          {paramKeys.map((k) => (
            <tr key={k} className="border-b border-[#1e2130]">
              <td className="px-4 py-1.5 text-gray-400 capitalize">{k.replace(/_/g, ' ')}</td>
              <td className={`px-4 py-1.5 text-right font-mono ${paramsA[k] !== paramsB[k] ? 'text-yellow-400' : 'text-gray-300'}`}>
                {String(paramsA[k] ?? '—')}
              </td>
              <td className={`px-4 py-1.5 text-right font-mono ${paramsA[k] !== paramsB[k] ? 'text-yellow-400' : 'text-gray-300'}`}>
                {String(paramsB[k] ?? '—')}
              </td>
            </tr>
          ))}

          {/* Metrics section */}
          <tr className="border-b border-[#1e2130] bg-[#0d0f17]">
            <td colSpan={3} className="px-4 py-1.5 text-gray-500 font-semibold uppercase tracking-wide text-[10px]">
              Metrics
            </td>
          </tr>
          {METRICS.map((m) => {
            const va = runA[m.key] as number | null;
            const vb = runB[m.key] as number | null;
            return (
              <tr key={m.key} className="border-b border-[#1e2130]">
                <td className="px-4 py-1.5 text-gray-400">{m.label}</td>
                <td className={`px-4 py-1.5 text-right font-medium ${cellColor(va, vb, m.higherIsBetter, 'a')}`}>
                  {m.format(va)}
                </td>
                <td className={`px-4 py-1.5 text-right font-medium ${cellColor(va, vb, m.higherIsBetter, 'b')}`}>
                  {m.format(vb)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
