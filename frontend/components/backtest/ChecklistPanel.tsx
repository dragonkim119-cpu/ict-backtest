'use client';

import type { ChecklistResult } from '@/lib/types';

interface Props {
  result: ChecklistResult;
}

const SCORE_COLOR = (score: number) => {
  if (score >= 6) return 'text-green-400';
  if (score >= 4) return 'text-yellow-400';
  return 'text-red-400';
};

export default function ChecklistPanel({ result }: Props) {
  return (
    <div className="rounded-lg border border-[#2a2e39] bg-[#131722] p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-white">
          ICT Checklist — {result.symbol} {result.interval}
          {result.htf_interval ? ` (HTF: ${result.htf_interval})` : ''}
        </h2>
        <span className={`text-lg font-bold ${SCORE_COLOR(result.score)}`}>
          {result.score}/7
        </span>
      </div>

      <div className="mb-2 text-xs text-gray-500 font-mono">
        Price: {result.price.toLocaleString()} · {new Date(result.evaluated_at).toUTCString()}
      </div>

      <ul className="space-y-1.5">
        {result.checks.map((item) => (
          <li key={item.id} className="flex items-start gap-2 text-sm">
            <span
              className={`mt-0.5 shrink-0 font-bold ${item.passed ? 'text-green-400' : 'text-red-400'}`}
            >
              {item.passed ? '✓' : '✗'}
            </span>
            <span className="text-gray-300">
              <span className="font-medium">{item.label}</span>
              {item.detail && (
                <span className="ml-1.5 text-gray-500 text-xs">{item.detail}</span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
