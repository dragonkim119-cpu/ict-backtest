'use client';

import { useEffect, useRef, useState } from 'react';

import { fetchMacroCalendar, fetchMacroNews, fetchMacroStatus } from '@/lib/api';
import type { EconomicEvent, MacroStatus, NewsItem } from '@/lib/types';

import EconomicCalendar from './EconomicCalendar';
import NewsFeed from './NewsFeed';

const INTERVALS = [
  { label: '1분', value: 1 },
  { label: '5분', value: 5 },
  { label: '15분', value: 15 },
  { label: '30분', value: 30 },
  { label: '1시간', value: 60 },
];

export default function MacroTab() {
  const [events, setEvents] = useState<EconomicEvent[]>([]);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [status, setStatus] = useState<MacroStatus | null>(null);
  const [calDays, setCalDays] = useState(7);
  const [refreshMin, setRefreshMin] = useState(15);
  const [newsTab, setNewsTab] = useState<'crypto' | 'macro'>('crypto');
  const [loading, setLoading] = useState(false);
  const [lastFetch, setLastFetch] = useState<string>('');
  const [error, setError] = useState('');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchAll = async () => {
    setLoading(true);
    setError('');
    try {
      const [cal, newsRes, st] = await Promise.all([
        fetchMacroCalendar(calDays),
        fetchMacroNews(),
        fetchMacroStatus(),
      ]);
      setEvents(cal.events);
      setNews(newsRes.items);
      setStatus(st);
      setLastFetch(new Date().toLocaleTimeString('ko-KR'));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  // Auto-refresh
  useEffect(() => {
    fetchAll();
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = setInterval(fetchAll, refreshMin * 60 * 1000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshMin, calDays]);

  const highImpact = events.filter((e) => e.impact === 'high');

  return (
    <div className="flex flex-col gap-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm text-gray-400">경제지표 범위:</span>
        <select
          value={calDays}
          onChange={(e) => setCalDays(Number(e.target.value))}
          className="px-2 py-1 rounded bg-[#1e2130] text-white text-sm border border-[#2a2e39]"
        >
          {[3, 7, 14, 30].map((d) => (
            <option key={d} value={d}>{d}일</option>
          ))}
        </select>

        <span className="text-sm text-gray-400">자동 갱신:</span>
        <select
          value={refreshMin}
          onChange={(e) => setRefreshMin(Number(e.target.value))}
          className="px-2 py-1 rounded bg-[#1e2130] text-white text-sm border border-[#2a2e39]"
        >
          {INTERVALS.map((iv) => (
            <option key={iv.value} value={iv.value}>{iv.label}</option>
          ))}
        </select>

        <button
          onClick={fetchAll}
          disabled={loading}
          className="px-3 py-1 rounded bg-[#2a2e39] hover:bg-[#363c4e] disabled:opacity-50 text-white text-sm transition-colors"
        >
          {loading ? '⟳ 불러오는 중…' : '↻ 새로고침'}
        </button>

        {lastFetch && <span className="text-xs text-gray-600">마지막 갱신: {lastFetch}</span>}

        {/* API 상태 표시 */}
        {status && (
          <div className="flex gap-2 ml-auto">
            <span className={`text-xs px-2 py-0.5 rounded ${status.finnhub ? 'bg-green-900 text-green-400' : 'bg-gray-800 text-gray-500'}`}>
              Finnhub {status.finnhub ? '✓' : '✗'}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded ${status.cryptopanic ? 'bg-green-900 text-green-400' : 'bg-gray-800 text-gray-500'}`}>
              CryptoPanic {status.cryptopanic ? '✓' : '✗'}
            </span>
          </div>
        )}
      </div>

      {error && <p className="text-xs text-red-400 font-mono">Error: {error}</p>}

      {/* High-impact alert banner */}
      {highImpact.length > 0 && (
        <div className="p-3 rounded border border-red-800 bg-red-950 text-sm text-red-300">
          <span className="font-bold">🔴 고임팩트 이벤트 {highImpact.length}건:</span>{' '}
          {highImpact.map((e) => `${e.event} (${e.date} ${e.time ?? ''})`).join(' · ')}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Economic Calendar */}
        <div className="bg-[#131722] rounded-lg border border-[#2a2e39] p-4">
          <h2 className="text-sm font-semibold text-white mb-3">
            📅 경제지표 캘린더 <span className="text-gray-500 font-normal">({events.length}건)</span>
          </h2>
          <EconomicCalendar events={events} />
        </div>

        {/* News Feed */}
        <div className="bg-[#131722] rounded-lg border border-[#2a2e39] p-4">
          <div className="flex items-center gap-2 mb-3">
            <h2 className="text-sm font-semibold text-white">📰 뉴스</h2>
            <div className="flex gap-1 ml-2">
              {(['crypto', 'macro'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setNewsTab(t)}
                  className={`px-2.5 py-0.5 rounded text-xs font-medium transition-colors ${
                    newsTab === t ? 'bg-[#2a2e39] text-white' : 'text-gray-500 hover:text-gray-300'
                  }`}
                >
                  {t === 'crypto' ? '크립토' : '거시경제'}
                </button>
              ))}
            </div>
          </div>
          <div className="overflow-y-auto max-h-[480px] pr-1">
            <NewsFeed items={news} tab={newsTab} />
          </div>
        </div>
      </div>
    </div>
  );
}
