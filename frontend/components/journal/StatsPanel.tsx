'use client';

import type { JournalStats, MonthStat } from '@/lib/types';

interface Props {
  stats: JournalStats;
}

function pct(rate: number) {
  return `${(rate * 100).toFixed(1)}%`;
}

function fmt(n: number | null, digits = 2) {
  if (n === null || n === undefined) return '—';
  return n.toFixed(digits);
}

// ── Summary cards ─────────────────────────────────────────────────

function SummaryCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-[#1e2130] rounded-lg p-3 flex flex-col gap-1">
      <span className="text-xs text-gray-500">{label}</span>
      <span className={`text-lg font-bold ${color ?? 'text-white'}`}>{value}</span>
    </div>
  );
}

// ── Bar (horizontal, normalized) ─────────────────────────────────

function HBar({ label, wins, total, pnl }: { label: string; wins: number; total: number; pnl?: number }) {
  const rate = total > 0 ? wins / total : 0;
  const pnlColor = pnl === undefined ? '' : pnl >= 0 ? 'text-green-400' : 'text-red-400';
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-400 w-10 text-right shrink-0">{label}</span>
      <div className="flex-1 h-4 bg-[#1a1e2e] rounded overflow-hidden">
        <div
          className="h-full rounded transition-all"
          style={{
            width: `${rate * 100}%`,
            background: rate >= 0.6 ? '#22c55e' : rate >= 0.4 ? '#eab308' : '#ef4444',
          }}
        />
      </div>
      <span className="text-xs text-gray-300 w-10 text-right shrink-0">{pct(rate)}</span>
      <span className="text-xs text-gray-500 w-8 text-right shrink-0">{total}</span>
      {pnl !== undefined && (
        <span className={`text-xs w-14 text-right shrink-0 font-mono ${pnlColor}`}>
          {pnl >= 0 ? '+' : ''}{pnl.toFixed(1)}R
        </span>
      )}
    </div>
  );
}

// ── Monthly PnL chart ─────────────────────────────────────────────

function MonthChart({ months }: { months: MonthStat[] }) {
  if (months.length === 0) return null;
  const maxAbs = Math.max(...months.map((m) => Math.abs(m.pnl_r)), 0.01);

  return (
    <div>
      <h3 className="text-xs font-semibold text-gray-400 mb-2">Monthly PnL (R)</h3>
      <div className="flex items-end gap-1 h-24">
        {months.map((m) => {
          const height = Math.abs(m.pnl_r) / maxAbs;
          const isPos = m.pnl_r >= 0;
          return (
            <div key={m.month} className="flex-1 flex flex-col items-center gap-0.5 min-w-0">
              {/* bar above/below zero line */}
              <div className="flex-1 w-full flex flex-col justify-end">
                {isPos && (
                  <div
                    className="w-full rounded-t"
                    style={{
                      height: `${height * 100}%`,
                      background: '#22c55e',
                      minHeight: m.pnl_r !== 0 ? 2 : 0,
                    }}
                  />
                )}
              </div>
              <div className="h-px w-full bg-[#2a2e39]" />
              <div className="flex-1 w-full flex flex-col justify-start">
                {!isPos && (
                  <div
                    className="w-full rounded-b"
                    style={{
                      height: `${height * 100}%`,
                      background: '#ef4444',
                      minHeight: m.pnl_r !== 0 ? 2 : 0,
                    }}
                  />
                )}
              </div>
              <span
                className="text-[8px] text-gray-500 truncate w-full text-center"
                title={m.month}
              >
                {m.month.slice(5)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────

export default function StatsPanel({ stats }: Props) {
  const { closed_total, wins, losses, win_rate, avg_rr, total_pnl_r } = stats;

  return (
    <div className="flex flex-col gap-4">
      {/* Summary */}
      <div>
        <h3 className="text-xs font-semibold text-gray-400 mb-2">Overview (closed trades)</h3>
        {closed_total === 0 ? (
          <p className="text-xs text-gray-500">No closed trades yet. Add result_pnl to see stats.</p>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            <SummaryCard label="Total Trades" value={String(closed_total)} />
            <SummaryCard
              label="Win Rate"
              value={pct(win_rate)}
              color={win_rate >= 0.5 ? 'text-green-400' : 'text-red-400'}
            />
            <SummaryCard
              label="Total PnL"
              value={`${total_pnl_r >= 0 ? '+' : ''}${fmt(total_pnl_r)}R`}
              color={total_pnl_r >= 0 ? 'text-green-400' : 'text-red-400'}
            />
            <SummaryCard label="Wins" value={String(wins)} color="text-green-400" />
            <SummaryCard label="Losses" value={String(losses)} color="text-red-400" />
            <SummaryCard label="Avg RR" value={avg_rr !== null ? fmt(avg_rr) : '—'} />
          </div>
        )}
      </div>

      {/* Monthly PnL */}
      {stats.by_month.length > 0 && (
        <div className="rounded-lg border border-[#2a2e39] bg-[#131722] p-3">
          <MonthChart months={stats.by_month} />
        </div>
      )}

      {/* By Direction */}
      {stats.by_direction.length > 0 && (
        <div className="rounded-lg border border-[#2a2e39] bg-[#131722] p-3">
          <h3 className="text-xs font-semibold text-gray-400 mb-2">By Direction</h3>
          <div className="flex flex-col gap-1.5">
            {stats.by_direction.map((d) => (
              <HBar
                key={d.direction}
                label={d.direction === 'long' ? '▲ L' : '▼ S'}
                wins={d.wins}
                total={d.total}
                pnl={d.avg_pnl_r !== null ? d.avg_pnl_r : undefined}
              />
            ))}
          </div>
          <p className="text-[10px] text-gray-600 mt-1.5">bar = win rate · last column = avg PnL R</p>
        </div>
      )}

      {/* By Weekday */}
      {stats.by_weekday.length > 0 && (
        <div className="rounded-lg border border-[#2a2e39] bg-[#131722] p-3">
          <h3 className="text-xs font-semibold text-gray-400 mb-2">By Weekday</h3>
          <div className="flex flex-col gap-1.5">
            {stats.by_weekday.map((d) => (
              <HBar key={d.day} label={d.day} wins={d.wins} total={d.total} />
            ))}
          </div>
        </div>
      )}

      {/* By Hour */}
      {stats.by_hour.length > 0 && (
        <div className="rounded-lg border border-[#2a2e39] bg-[#131722] p-3">
          <h3 className="text-xs font-semibold text-gray-400 mb-2">By Hour (UTC)</h3>
          <div className="flex flex-col gap-1">
            {stats.by_hour.map((h) => (
              <HBar
                key={h.hour}
                label={`${String(h.hour).padStart(2, '0')}h`}
                wins={h.wins}
                total={h.total}
              />
            ))}
          </div>
        </div>
      )}

      {/* By Interval */}
      {stats.by_interval.length > 0 && (
        <div className="rounded-lg border border-[#2a2e39] bg-[#131722] p-3">
          <h3 className="text-xs font-semibold text-gray-400 mb-2">By Timeframe</h3>
          <div className="flex flex-col gap-1.5">
            {stats.by_interval.map((i) => (
              <HBar key={i.interval} label={i.interval} wins={i.wins} total={i.total} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
