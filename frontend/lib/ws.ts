'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import type { BPR, Candle, FVG, IFVG, KillZoneSpan, LiquidityPool, PO3, Sweep } from './types';

const WS_BASE = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
  .replace(/^http/, 'ws');

export type WsStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface LiveCandle extends Candle {
  closed: boolean;
}

export interface PatternUpdate {
  symbol: string;
  interval: string;
  fvgs: FVG[];
  ifvgs: IFVG[];
  bprs: BPR[];
  sweeps: Sweep[];
  liquidities: LiquidityPool[];
  killzones: KillZoneSpan[];
  po3s: PO3[];
}

export function useKlineStream(
  symbol: string,
  interval: string,
  enabled: boolean,
) {
  const [status, setStatus] = useState<WsStatus>('disconnected');
  const [liveCandle, setLiveCandle] = useState<LiveCandle | null>(null);
  const [patternUpdate, setPatternUpdate] = useState<PatternUpdate | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const enabledRef = useRef(enabled);
  enabledRef.current = enabled;

  const connect = useCallback(() => {
    if (!enabledRef.current) return;

    const url = `${WS_BASE}/ws/kline?symbol=${symbol}&interval=${interval}`;
    setStatus('connecting');

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setStatus('connected');

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data as string);
        if (msg.type === 'kline') {
          setLiveCandle({ ...msg.candle, closed: msg.candle.closed });
        } else if (msg.type === 'patterns') {
          setPatternUpdate(msg as PatternUpdate);
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onerror = () => setStatus('error');

    ws.onclose = () => {
      setStatus('disconnected');
      wsRef.current = null;
      if (enabledRef.current) {
        reconnectTimer.current = setTimeout(connect, 3000);
      }
    };
  }, [symbol, interval]);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
      wsRef.current = null;
      setStatus('disconnected');
      setLiveCandle(null);
      setPatternUpdate(null);
    }

    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [enabled, connect]);

  return { status, liveCandle, patternUpdate };
}
