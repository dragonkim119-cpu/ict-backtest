'use client';

import { useEffect, useRef } from 'react';
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  LineStyle,
  createChart,
  createSeriesMarkers,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts';

import {
  BoxesPrimitive,
  KillZonePrimitive,
  KZ_COLORS,
  toUTC,
  type Box,
  type KillZone,
} from '@/lib/chart-primitives';
import type { BPR, Candle, FVG, IFVG, KillZoneSpan, LiquidityPool, PO3, Sweep, Trade } from '@/lib/types';

interface Visibility {
  fvg: boolean;
  ifvg: boolean;
  bpr: boolean;
  liquidity: boolean;
  sweeps: boolean;
  killzones: boolean;
  po3: boolean;
}

interface Props {
  candles: Candle[];
  fvgs: FVG[];
  ifvgs: IFVG[];
  bprs: BPR[];
  liquidities: LiquidityPool[];
  sweeps: Sweep[];
  killzones: KillZoneSpan[];
  po3s: PO3[];
  htfBprs?: BPR[];
  visibility: Visibility;
  trades?: Trade[];
  liveMode?: boolean;
}

type AnyPrimitive = BoxesPrimitive | KillZonePrimitive;

export default function CandleChart({
  candles,
  fvgs,
  ifvgs,
  bprs,
  liquidities,
  sweeps,
  killzones,
  po3s = [],
  htfBprs = [],
  visibility,
  trades,
  liveMode,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const primitivesRef = useRef<AnyPrimitive[]>([]);
  const priceLinesRef = useRef<IPriceLine[]>([]);
  const markersPluginRef = useRef<ReturnType<typeof createSeriesMarkers<Time>> | null>(null);
  // Stable ref so overlay effect doesn't re-run on every tick
  const candlesRef = useRef(candles);
  candlesRef.current = candles;
  const prevLengthRef = useRef(0);

  // Create chart once
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#131722' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#1e2130' },
        horzLines: { color: '#1e2130' },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#2a2e39' },
      timeScale: { borderColor: '#2a2e39', timeVisible: true },
      width: containerRef.current.clientWidth,
      height: 600,
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderUpColor: '#26a69a',
      borderDownColor: '#ef5350',
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const observer = new ResizeObserver(() => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // Update candle data — use series.update() for live ticks, setData() for full reloads
  useEffect(() => {
    if (!seriesRef.current || candles.length === 0) return;
    const isLiveTick = liveMode && Math.abs(candles.length - prevLengthRef.current) <= 1 && prevLengthRef.current > 0;
    prevLengthRef.current = candles.length;

    if (isLiveTick) {
      const last = candles[candles.length - 1];
      seriesRef.current.update({
        time: toUTC(last.open_time),
        open: last.open,
        high: last.high,
        low: last.low,
        close: last.close,
      });
      chartRef.current?.timeScale().scrollToRealTime();
    } else {
      seriesRef.current.setData(
        candles.map((c) => ({
          time: toUTC(c.open_time),
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        })),
      );
      chartRef.current?.timeScale().fitContent();
    }
  }, [candles, liveMode]);

  // Update overlays when patterns or visibility changes (NOT on every candle tick)
  // candlesRef is used instead of candles to avoid re-running on live ticks.
  useEffect(() => {
    const chart = chartRef.current;
    const series = seriesRef.current;
    const candles = candlesRef.current;
    if (!chart || !series || candles.length === 0) return;

    // Remove old overlays
    primitivesRef.current.forEach((p) => series.detachPrimitive(p as never));
    primitivesRef.current = [];
    priceLinesRef.current.forEach((pl) => series.removePriceLine(pl));
    priceLinesRef.current = [];
    if (markersPluginRef.current) {
      markersPluginRef.current.detach();
      markersPluginRef.current = null;
    }

    const lastTime = toUTC(candles[candles.length - 1].open_time);

    const attachBoxes = (boxes: Box[]) => {
      if (boxes.length === 0) return;
      const p = new BoxesPrimitive(chart, series, boxes);
      series.attachPrimitive(p as never);
      primitivesRef.current.push(p);
    };

    // Kill zone backgrounds (drawn first → behind everything)
    if (visibility.killzones) {
      const zones: KillZone[] = killzones.map((kz) => ({
        time1: toUTC(kz.start_time),
        time2: toUTC(kz.end_time),
        color: KZ_COLORS[kz.name] ?? 'rgba(128,128,128,0.06)',
      }));
      if (zones.length > 0) {
        const p = new KillZonePrimitive(chart, zones);
        series.attachPrimitive(p as never);
        primitivesRef.current.push(p);
      }
    }

    // PO3 / AMD phases (boxes only — markers added after allMarkers is declared below)
    if (visibility.po3 && po3s.length > 0) {
      const accumBoxes: Box[] = [];
      const distribBoxes: Box[] = [];

      for (const p of po3s) {
        const isBull = p.type === 'bull';
        accumBoxes.push({
          time1: toUTC(p.accum_start_time),
          time2: toUTC(p.accum_end_time),
          price1: p.accum_low,
          price2: p.accum_high,
          fillColor: 'rgba(156,163,175,0.12)',
          borderColor: 'rgba(156,163,175,0.5)',
        });
        const distribEnd = p.distrib_end_time ? toUTC(p.distrib_end_time) : lastTime;
        distribBoxes.push({
          time1: toUTC(p.distrib_start_time),
          time2: distribEnd,
          price1: isBull ? p.accum_low : p.accum_high - (p.accum_high - p.accum_low) * 3,
          price2: isBull ? p.accum_high + (p.accum_high - p.accum_low) * 3 : p.accum_high,
          fillColor: isBull ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
          borderColor: isBull ? 'rgba(34,197,94,0.4)' : 'rgba(239,68,68,0.4)',
        });
      }

      attachBoxes(accumBoxes);
      attachBoxes(distribBoxes);
    }

    // FVG boxes — use created_time as start (works for both historical and live pattern updates)
    if (visibility.fvg) {
      attachBoxes(
        fvgs.map((f) => {
          const endTime =
            f.mitigated && f.mitigated_time ? toUTC(f.mitigated_time) : lastTime;
          return {
            time1: toUTC(f.created_time),
            time2: endTime,
            price1: f.bottom,
            price2: f.top,
            fillColor: f.type === 'bull' ? 'rgba(38,166,154,0.15)' : 'rgba(239,83,80,0.15)',
            borderColor: f.type === 'bull' ? 'rgba(38,166,154,0.5)' : 'rgba(239,83,80,0.5)',
          };
        }),
      );
    }

    // IFVG boxes
    if (visibility.ifvg) {
      attachBoxes(
        ifvgs.map((f) => ({
          time1: toUTC(f.created_time),
          time2: lastTime,
          price1: f.bottom,
          price2: f.top,
          fillColor: f.type === 'bull' ? 'rgba(38,166,154,0.08)' : 'rgba(239,83,80,0.08)',
          borderColor: f.type === 'bull' ? 'rgba(38,166,154,0.35)' : 'rgba(239,83,80,0.35)',
        })),
      );
    }

    // HTF BPR zones (gold, rendered behind LTF BPRs)
    if (htfBprs && htfBprs.length > 0) {
      attachBoxes(
        htfBprs.map((b) => ({
          time1: toUTC(b.created_time),
          time2: lastTime,
          price1: b.bottom,
          price2: b.top,
          fillColor: 'rgba(234,179,8,0.1)',
          borderColor: 'rgba(234,179,8,0.7)',
        })),
      );
    }

    // BPR boxes (brighter/thicker border)
    if (visibility.bpr) {
      attachBoxes(
        bprs.map((b) => ({
          time1: toUTC(b.created_time),
          time2: lastTime,
          price1: b.bottom,
          price2: b.top,
          fillColor: b.type === 'bull' ? 'rgba(38,166,154,0.25)' : 'rgba(239,83,80,0.25)',
          borderColor: b.type === 'bull' ? 'rgba(38,166,154,0.9)' : 'rgba(239,83,80,0.9)',
        })),
      );
    }

    // Liquidity pool price lines
    if (visibility.liquidity) {
      liquidities.forEach((pool) => {
        const pl = series.createPriceLine({
          price: pool.level,
          color: pool.side === 'BSL' ? '#ef4444' : '#22c55e',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: `${pool.side}${pool.swept ? '✓' : ''}`,
        });
        priceLinesRef.current.push(pl);
      });
    }

    // Sweep markers + trade entry/exit markers + PO3 manipulation markers (combined)
    const allMarkers: Parameters<typeof createSeriesMarkers<Time>>[1] = [];

    // PO3 manipulation candle markers (orange)
    if (visibility.po3) {
      for (const p of po3s) {
        allMarkers.push({
          time: toUTC(p.manip_time),
          position: p.type === 'bull' ? ('belowBar' as const) : ('aboveBar' as const),
          color: '#f97316',
          shape: p.type === 'bull' ? ('arrowUp' as const) : ('arrowDown' as const),
          size: 2 as const,
          text: `M(${p.session === 'London' ? 'L' : 'N'})`,
        });
      }
    }

    if (visibility.sweeps) {
      for (const s of sweeps) {
        allMarkers.push({
          time: toUTC(s.sweep_time),
          position: s.type === 'bear' ? ('aboveBar' as const) : ('belowBar' as const),
          color: s.type === 'bear' ? '#ef4444' : '#22c55e',
          shape: s.type === 'bear' ? ('arrowDown' as const) : ('arrowUp' as const),
          size: 1 as const,
        });
      }
    }

    if (trades && trades.length > 0) {
      for (const t of trades) {
        allMarkers.push({
          time: toUTC(t.entry.entry_time),
          position: t.entry.direction === 'long' ? ('belowBar' as const) : ('aboveBar' as const),
          color: t.entry.direction === 'long' ? '#3b82f6' : '#a855f7',
          shape: t.entry.direction === 'long' ? ('arrowUp' as const) : ('arrowDown' as const),
          size: 2 as const,
          text: t.entry.direction === 'long' ? 'E↑' : 'E↓',
        });
        const exitColor =
          t.status === 'closed_win' ? '#22c55e' : t.status === 'closed_loss' ? '#ef4444' : '#f59e0b';
        allMarkers.push({
          time: toUTC(t.exit_time),
          position: t.entry.direction === 'long' ? ('aboveBar' as const) : ('belowBar' as const),
          color: exitColor,
          shape: 'circle' as const,
          size: 1 as const,
          text: t.status === 'closed_win' ? 'X✓' : t.status === 'closed_loss' ? 'X✗' : 'XT',
        });
      }
    }

    if (allMarkers.length > 0) {
      allMarkers.sort((a, b) => (a.time as number) - (b.time as number));
      markersPluginRef.current = createSeriesMarkers<Time>(series, allMarkers);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fvgs, ifvgs, bprs, liquidities, sweeps, killzones, po3s, htfBprs, visibility, trades]);

  return (
    <div
      ref={containerRef}
      className="w-full rounded-lg overflow-hidden border border-[#2a2e39]"
      style={{ height: 600 }}
    />
  );
}
