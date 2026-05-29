'use client';

import type { Metrics } from '@/lib/types';

interface Props {
  metrics: Metrics;
  runId: string;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 px-3 py-2 bg-[#1a1d2e] rounded">
      <span className="text-[10px] text-gray-500 uppercase tracking-wide">{label}</span>
      <span className="text-sm font-mono text-white">{value}</span>
    </div>
  );
}

export default function MetricsPanel({ metrics, runId }: Props) {
  const pf =
    metrics.profit_factor == null ? '—'
    : !isFinite(metrics.profit_factor) ? '∞'
    : metrics.profit_factor.toFixed(2);

  return (
    <div className="rounded-lg border border-[#2a2e39] p-3 bg-[#131722]">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold text-white">Backtest Results</h2>
        <span className="text-[10px] text-gray-600 font-mono">{runId}</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2">
        <Stat label="Trades" value={String(metrics.total_trades)} />
        <Stat
          label="Win Rate"
          value={`${(metrics.win_rate * 100).toFixed(1)}% (${metrics.wins}W / ${metrics.losses}L)`}
        />
        <Stat label="Profit Factor" value={pf} />
        <Stat label="Expectancy" value={`${metrics.expectancy.toFixed(3)}R`} />
        <Stat label="Total PnL" value={`${metrics.total_pnl_r.toFixed(2)}R`} />
        <Stat label="Max DD" value={`${metrics.max_drawdown_r.toFixed(2)}R`} />
        <Stat label="Max Consec. Loss" value={String(metrics.max_consecutive_losses)} />
        <Stat label="Timeouts" value={String(metrics.timeouts)} />
        <Stat
          label="Avg Duration"
          value={`${metrics.avg_trade_duration_candles.toFixed(1)} candles`}
        />
      </div>
    </div>
  );
}
