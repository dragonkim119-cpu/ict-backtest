'use client';

import type { EconomicEvent } from '@/lib/types';

const IMPACT_COLOR: Record<string, string> = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#6b7280',
};

const IMPACT_DOT: Record<string, string> = {
  high: '🔴',
  medium: '🟡',
  low: '⚪',
};

function fmtTime(date: string, time: string | null): string {
  if (!time) return date;
  // Convert UTC time to KST (+9)
  const dt = new Date(`${date}T${time}Z`);
  return dt.toLocaleString('ko-KR', {
    month: 'numeric', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
    timeZone: 'Asia/Seoul',
  }) + ' KST';
}

export default function EconomicCalendar({ events }: { events: EconomicEvent[] }) {
  if (events.length === 0) {
    return <p className="text-xs text-gray-500 py-4 text-center">이벤트 없음 (Finnhub API 키 확인)</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-gray-500 border-b border-[#2a2e39]">
            <th className="text-left py-1.5 pr-3 font-medium">임팩트</th>
            <th className="text-left py-1.5 pr-3 font-medium">이벤트</th>
            <th className="text-left py-1.5 pr-3 font-medium">시간 (KST)</th>
            <th className="text-right py-1.5 pr-3 font-medium">예상</th>
            <th className="text-right py-1.5 pr-3 font-medium">이전</th>
            <th className="text-right py-1.5 font-medium">실제</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e, i) => (
            <tr
              key={i}
              className="border-b border-[#1e2130] hover:bg-[#1e2130] transition-colors"
            >
              <td className="py-1.5 pr-3">
                <span title={e.impact ?? ''}>
                  {IMPACT_DOT[e.impact ?? ''] ?? '⚪'}
                </span>
              </td>
              <td className="py-1.5 pr-3 text-white font-medium max-w-[200px] truncate">{e.event}</td>
              <td className="py-1.5 pr-3 text-gray-400 whitespace-nowrap">{fmtTime(e.date, e.time)}</td>
              <td className="py-1.5 pr-3 text-right text-gray-300">
                {e.estimate != null ? `${e.estimate}${e.unit ?? ''}` : '—'}
              </td>
              <td className="py-1.5 pr-3 text-right text-gray-500">
                {e.prev != null ? `${e.prev}${e.unit ?? ''}` : '—'}
              </td>
              <td className="py-1.5 text-right font-bold">
                {e.actual != null ? (
                  <span style={{ color: IMPACT_COLOR[e.impact ?? ''] ?? '#d1d4dc' }}>
                    {e.actual}{e.unit ?? ''}
                  </span>
                ) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
