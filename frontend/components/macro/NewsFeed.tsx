'use client';

import type { NewsItem } from '@/lib/types';

const IMPORTANCE_COLOR: Record<string, string> = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#6b7280',
};

const IMPORTANCE_BADGE: Record<string, string> = {
  high: 'bg-red-900 text-red-300',
  medium: 'bg-yellow-900 text-yellow-300',
  low: 'bg-gray-800 text-gray-400',
};

function relTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60) return `${m}분 전`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}시간 전`;
  return `${Math.floor(h / 24)}일 전`;
}

export default function NewsFeed({ items, tab }: { items: NewsItem[]; tab: 'crypto' | 'macro' }) {
  const filtered = items.filter((n) =>
    tab === 'crypto' ? n.currencies.includes('BTC') : n.currencies.length === 0,
  );

  if (filtered.length === 0) {
    return (
      <p className="text-xs text-gray-500 py-4 text-center">
        {tab === 'crypto' ? 'CryptoPanic API 키 확인' : 'Finnhub API 키 확인'}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {filtered.map((n, i) => (
        <a
          key={i}
          href={n.url}
          target="_blank"
          rel="noopener noreferrer"
          className="block p-2.5 rounded bg-[#1a1d2a] hover:bg-[#1e2130] border border-[#2a2e39] transition-colors"
        >
          <div className="flex items-start justify-between gap-2">
            <span className="text-sm text-white leading-snug">{n.title}</span>
            {n.importance && (
              <span className={`text-xs px-1.5 py-0.5 rounded shrink-0 font-medium ${IMPORTANCE_BADGE[n.importance] ?? ''}`}>
                {n.importance.toUpperCase()}
              </span>
            )}
          </div>
          {n.summary && (
            <p className="text-xs text-gray-500 mt-1 line-clamp-2">{n.summary}</p>
          )}
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-gray-600">{n.source}</span>
            <span className="text-xs text-gray-600">·</span>
            <span className="text-xs text-gray-600">{relTime(n.published_at)}</span>
          </div>
        </a>
      ))}
    </div>
  );
}
