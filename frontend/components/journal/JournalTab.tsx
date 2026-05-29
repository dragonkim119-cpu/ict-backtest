'use client';

import { useCallback, useEffect, useState } from 'react';

import {
  compareJournalEntry,
  createJournalEntry,
  deleteJournalEntry,
  fetchJournalEntries,
  fetchJournalStats,
  fetchJournalVsBacktest,
  updateJournalEntry,
} from '@/lib/api';
import type { JournalEntry, JournalEntryCreate, JournalStats, JournalVsBacktest } from '@/lib/types';

import BacktestCompare from './BacktestCompare';
import JournalDetail from './JournalDetail';
import JournalForm from './JournalForm';
import StatsPanel from './StatsPanel';
import JournalTable from './JournalTable';

type SubTab = 'entries' | 'stats';
type RightPanel = 'none' | 'form' | 'detail';

export default function JournalTab() {
  const [subTab, setSubTab] = useState<SubTab>('entries');

  // ── Entries state ──────────────────────────────────────────────
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [selectedEntry, setSelectedEntry] = useState<JournalEntry | null>(null);
  const [rightPanel, setRightPanel] = useState<RightPanel>('none');
  const [filterDir, setFilterDir] = useState<'' | 'long' | 'short'>('');
  const [filterInterval, setFilterInterval] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // ── Stats state ────────────────────────────────────────────────
  const [stats, setStats] = useState<JournalStats | null>(null);
  const [vsBacktest, setVsBacktest] = useState<JournalVsBacktest | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [statsError, setStatsError] = useState('');

  const loadEntries = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchJournalEntries({
        direction: filterDir || undefined,
        interval: filterInterval || undefined,
      });
      setEntries(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [filterDir, filterInterval]);

  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    setStatsError('');
    try {
      const [s, v] = await Promise.all([fetchJournalStats(), fetchJournalVsBacktest()]);
      setStats(s);
      setVsBacktest(v);
    } catch (err) {
      setStatsError(err instanceof Error ? err.message : String(err));
    } finally {
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadEntries();
  }, [loadEntries]);

  useEffect(() => {
    if (subTab === 'stats') void loadStats();
  }, [subTab, loadStats]);

  const handleCreate = async (data: JournalEntryCreate): Promise<JournalEntry> => {
    const created = await createJournalEntry(data);
    setEntries((prev) => [created, ...prev]);
    return created;
  };

  const handleCreated = (entry: JournalEntry) => {
    setSelectedEntry(entry);
    setRightPanel('detail');
  };

  const handleSelect = (entry: JournalEntry) => {
    setSelectedEntry(entry);
    setRightPanel('detail');
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteJournalEntry(id);
      setEntries((prev) => prev.filter((e) => e.id !== id));
      if (selectedEntry?.id === id) {
        setSelectedEntry(null);
        setRightPanel('none');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleUpdate = async (update: Parameters<typeof updateJournalEntry>[1]): Promise<JournalEntry> => {
    if (!selectedEntry) throw new Error('No entry selected');
    const updated = await updateJournalEntry(selectedEntry.id, update);
    setEntries((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
    setSelectedEntry(updated);
    return updated;
  };

  const INTERVALS = ['', '1m', '5m', '15m', '1h', '4h', '1d'];

  return (
    <div className="flex flex-col gap-3">
      {/* Sub-tab bar */}
      <div className="flex gap-1 border-b border-[#2a2e39] pb-2">
        {(['entries', 'stats'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setSubTab(t)}
            className={`px-4 py-1 rounded text-sm transition-colors ${
              subTab === t
                ? 'bg-[#2a2e39] text-white font-medium'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {t === 'entries' ? 'Entries' : 'Statistics'}
          </button>
        ))}
      </div>

      {/* ── Entries tab ────────────────────────────────────────── */}
      {subTab === 'entries' && (
        <>
          {/* Toolbar */}
          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={() => setRightPanel(rightPanel === 'form' ? 'none' : 'form')}
              className={`px-4 py-1.5 rounded text-sm font-semibold transition-colors ${
                rightPanel === 'form'
                  ? 'bg-blue-600 text-white'
                  : 'bg-[#1e2130] hover:bg-[#2a2e39] text-blue-400 border border-blue-800'
              }`}
            >
              + New Entry
            </button>

            <div className="flex items-center gap-1.5">
              <span className="text-xs text-gray-500">Direction:</span>
              {(['', 'long', 'short'] as const).map((d) => (
                <button
                  key={d}
                  onClick={() => setFilterDir(d)}
                  className={`px-2.5 py-1 rounded text-xs transition-colors ${
                    filterDir === d
                      ? d === 'long'
                        ? 'bg-green-700 text-white'
                        : d === 'short'
                        ? 'bg-red-700 text-white'
                        : 'bg-[#2a2e39] text-white'
                      : 'bg-transparent text-gray-500 hover:text-white border border-[#2a2e39]'
                  }`}
                >
                  {d === '' ? 'All' : d === 'long' ? '▲ Long' : '▼ Short'}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-xs text-gray-500">TF:</span>
              <select
                value={filterInterval}
                onChange={(e) => setFilterInterval(e.target.value)}
                className="px-2 py-1 rounded bg-[#1e2130] text-white text-xs border border-[#2a2e39]"
              >
                {INTERVALS.map((i) => <option key={i} value={i}>{i || 'All'}</option>)}
              </select>
            </div>

            <span className="text-xs text-gray-500 ml-auto">
              {entries.length} {entries.length === 1 ? 'entry' : 'entries'}
            </span>
          </div>

          {error && <p className="text-xs text-red-400 font-mono">Error: {error}</p>}
          {loading && <p className="text-xs text-gray-500">Loading…</p>}

          {/* Table + right panel */}
          <div className="flex gap-4 items-start">
            <div className="flex-1 min-w-0">
              <JournalTable
                entries={entries}
                selectedId={selectedEntry?.id ?? null}
                onSelect={handleSelect}
                onDelete={(id) => void handleDelete(id)}
              />
            </div>

            {rightPanel !== 'none' && (
              <div className="w-80 shrink-0 rounded-lg border border-[#2a2e39] bg-[#131722] p-4">
                {rightPanel === 'form' && (
                  <JournalForm
                    onCreate={handleCreate}
                    onCreated={handleCreated}
                    onCancel={() => setRightPanel('none')}
                  />
                )}
                {rightPanel === 'detail' && selectedEntry && (
                  <JournalDetail
                    entry={selectedEntry}
                    onClose={() => setRightPanel('none')}
                    onUpdate={handleUpdate}
                    onCompare={compareJournalEntry}
                  />
                )}
              </div>
            )}
          </div>
        </>
      )}

      {/* ── Stats tab ──────────────────────────────────────────── */}
      {subTab === 'stats' && (
        <div className="flex flex-col gap-4">
          {statsLoading && <p className="text-xs text-gray-500">Loading statistics…</p>}
          {statsError && <p className="text-xs text-red-400 font-mono">Error: {statsError}</p>}

          {stats && (
            <div className="flex gap-4 items-start flex-wrap lg:flex-nowrap">
              {/* Left: journal stats */}
              <div className="flex-1 min-w-0 flex flex-col gap-4">
                <StatsPanel stats={stats} />
              </div>
              {/* Right: vs backtest */}
              {vsBacktest && (
                <div className="w-80 shrink-0">
                  <BacktestCompare data={vsBacktest} />
                </div>
              )}
            </div>
          )}

          {!statsLoading && !stats && !statsError && (
            <p className="text-xs text-gray-500">No statistics available yet.</p>
          )}
        </div>
      )}
    </div>
  );
}
