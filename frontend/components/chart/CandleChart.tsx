'use client';

import { useEffect, useRef } from 'react';
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  LineStyle,
  createChart,
  createSeriesMarkers,
  type BusinessDay,
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
import type {
  BPR, Candle, DonchianPoint, FVG, IFVG, KillZoneSpan,
  LiquidityPool, PO3, Sweep, Trade, TurtleDonchianResponse,
} from '@/lib/types';

interface Visibility {
  fvg: boolean;
  ifvg: boolean;
  bpr: boolean;
  liquidity: boolean;
  sweeps: boolean;
  killzones: boolean;
  po3: boolean;
  turtle_s1: boolean;
  turtle_s2: boolean;
  ma20: boolean;
  ma50: boolean;
  ma200: boolean;
  ema50: boolean;
  vwap: boolean;
  volume: boolean;
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
  turtleData?: TurtleDonchianResponse | null;
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
  turtleData,
  visibility,
  trades,
  liveMode,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const primitivesRef = useRef<AnyPrimitive[]>([]);
  const priceLinesRef = useRef<IPriceLine[]>([]);
  const markersPluginRef = useRef<ReturnType<typeof createSeriesMarkers<Time>> | null>(null);
  // Stable ref so overlay effect doesn't re-run on every tick
  const candlesRef = useRef(candles);
  candlesRef.current = candles;
  const prevLengthRef = useRef(0);
  const lastSeriesTimeRef = useRef<number>(0);
  const s1UpperRef = useRef<ISeriesApi<'Line'> | null>(null);
  const s1LowerRef = useRef<ISeriesApi<'Line'> | null>(null);
  const s2UpperRef = useRef<ISeriesApi<'Line'> | null>(null);
  const s2LowerRef = useRef<ISeriesApi<'Line'> | null>(null);
  const ma20Ref = useRef<ISeriesApi<'Line'> | null>(null);
  const ma50Ref = useRef<ISeriesApi<'Line'> | null>(null);
  const ma200Ref = useRef<ISeriesApi<'Line'> | null>(null);
  const ema50Ref = useRef<ISeriesApi<'Line'> | null>(null);
  const vwapRef = useRef<ISeriesApi<'Line'> | null>(null);
  const volumeRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  // Create chart once
  useEffect(() => {
    if (!containerRef.current) return;

    const fmtKST = (t: UTCTimestamp | BusinessDay): string => {
      if (typeof t !== 'number') return '';
      const d = new Date(t * 1000);
      const yy = d.getUTCFullYear();
      const mo = String(d.getUTCMonth() + 1).padStart(2, '0');
      const dd = String(d.getUTCDate()).padStart(2, '0');
      const hh = String(d.getUTCHours()).padStart(2, '0');
      const mm = String(d.getUTCMinutes()).padStart(2, '0');
      return `${yy}-${mo}-${dd} ${hh}:${mm} KST`;
    };

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
      localization: { timeFormatter: fmtKST },
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

    // Donchian channel line series (hidden until turtleData is loaded)
    const lineOpts = { lineWidth: 1 as const, lastValueVisible: false, priceLineVisible: false };
    s1UpperRef.current = chart.addSeries(LineSeries, { ...lineOpts, color: 'rgba(34,197,94,0.7)', lineStyle: LineStyle.Dashed });
    s1LowerRef.current = chart.addSeries(LineSeries, { ...lineOpts, color: 'rgba(34,197,94,0.5)', lineStyle: LineStyle.Dotted });
    s2UpperRef.current = chart.addSeries(LineSeries, { ...lineOpts, color: 'rgba(96,165,250,0.7)', lineStyle: LineStyle.Dashed });
    s2LowerRef.current = chart.addSeries(LineSeries, { ...lineOpts, color: 'rgba(96,165,250,0.5)', lineStyle: LineStyle.Dotted });

    // Moving average line series
    const maOpts = { lineWidth: 1 as const, lastValueVisible: true, priceLineVisible: false };
    ma20Ref.current = chart.addSeries(LineSeries, { ...maOpts, color: 'rgba(245,158,11,0.85)', title: 'MA20' });
    ma50Ref.current = chart.addSeries(LineSeries, { ...maOpts, color: 'rgba(59,130,246,0.85)', title: 'MA50' });
    ma200Ref.current = chart.addSeries(LineSeries, { ...maOpts, color: 'rgba(239,68,68,0.85)', lineWidth: 2 as const, title: 'MA200' });
    ema50Ref.current = chart.addSeries(LineSeries, { ...maOpts, color: 'rgba(168,85,247,0.85)', lineStyle: LineStyle.Dashed, title: 'EMA50' });
    vwapRef.current = chart.addSeries(LineSeries, { lineWidth: 2 as const, lastValueVisible: true, priceLineVisible: false, color: 'rgba(255,255,255,0.8)', title: 'VWAP' });
    volumeRef.current = chart.addSeries(HistogramSeries, {
      priceScaleId: 'volume',
      lastValueVisible: false,
      priceLineVisible: false,
    });
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });

    // OHLC crosshair tooltip
    chart.subscribeCrosshairMove((param) => {
      const tooltip = tooltipRef.current;
      if (!tooltip) return;
      if (!param.time || !param.point) {
        tooltip.style.display = 'none';
        return;
      }
      const bar = param.seriesData.get(series) as
        | { open: number; high: number; low: number; close: number } | undefined;
      if (!bar) {
        tooltip.style.display = 'none';
        return;
      }
      const up = bar.close >= bar.open;
      const color = up ? '#26a69a' : '#ef5350';
      const fmt = (n: number) => n.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

      const getMaVal = (ref: React.RefObject<ISeriesApi<'Line'> | null>) => {
        if (!ref.current) return null;
        const d = param.seriesData.get(ref.current) as { value: number } | undefined;
        return d?.value ?? null;
      };
      const ma20Val = getMaVal(ma20Ref);
      const ma50Val = getMaVal(ma50Ref);
      const ma200Val = getMaVal(ma200Ref);
      const ema50Val = getMaVal(ema50Ref);
      const vwapVal = getMaVal(vwapRef);
      const maHtml = [
        ma20Val !== null ? `<span style="color:#f59e0b">MA20 <b>${fmt(ma20Val)}</b></span>` : '',
        ma50Val !== null ? `<span style="color:#3b82f6">MA50 <b>${fmt(ma50Val)}</b></span>` : '',
        ma200Val !== null ? `<span style="color:#ef4444">MA200 <b>${fmt(ma200Val)}</b></span>` : '',
        ema50Val !== null ? `<span style="color:#a855f7">EMA50 <b>${fmt(ema50Val)}</b></span>` : '',
        vwapVal !== null ? `<span style="color:rgba(255,255,255,0.9)">VWAP <b>${fmt(vwapVal)}</b></span>` : '',
      ].filter(Boolean).join('  ');

      tooltip.innerHTML =
        `<span style="color:${color};font-weight:700">` +
        `O <b>${fmt(bar.open)}</b>  H <b>${fmt(bar.high)}</b>  L <b>${fmt(bar.low)}</b>  C <b>${fmt(bar.close)}</b>` +
        `</span>` +
        (maHtml ? `&nbsp;&nbsp;&nbsp;<span style="opacity:0.75">${maHtml}</span>` : '');
      tooltip.style.display = 'block';
    });

    const observer = new ResizeObserver(() => {
      const w = containerRef.current?.clientWidth ?? 0;
      if (w > 0) chart.applyOptions({ width: w });
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      s1UpperRef.current = null;
      s1LowerRef.current = null;
      s2UpperRef.current = null;
      s2LowerRef.current = null;
      ma20Ref.current = null;
      ma50Ref.current = null;
      ma200Ref.current = null;
      ema50Ref.current = null;
      vwapRef.current = null;
      volumeRef.current = null;
    };
  }, []);

  // Update candle data — use series.update() for live ticks, setData() for full reloads
  useEffect(() => {
    if (!seriesRef.current || candles.length === 0) return;
    const isLiveTick = liveMode && Math.abs(candles.length - prevLengthRef.current) <= 1 && prevLengthRef.current > 0;
    prevLengthRef.current = candles.length;

    if (isLiveTick) {
      const last = candles[candles.length - 1];
      const newTime = toUTC(last.open_time);
      // Guard: skip update if time regressed (stale candle from interval switch)
      if (newTime >= lastSeriesTimeRef.current) {
        seriesRef.current.update({
          time: newTime,
          open: last.open,
          high: last.high,
          low: last.low,
          close: last.close,
        });
        lastSeriesTimeRef.current = newTime;
        // Only auto-scroll if user is already near the right edge (not viewing history)
        const lr = chartRef.current?.timeScale().getVisibleLogicalRange();
        const atEdge = lr ? lr.to >= prevLengthRef.current - 3 : true;
        if (atEdge) chartRef.current?.timeScale().scrollToRealTime();
      }
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
      lastSeriesTimeRef.current = toUTC(candles[candles.length - 1].open_time);
      chartRef.current?.timeScale().fitContent();
    }
  }, [candles, liveMode]);

  // Volume histogram + candle scale margin adjustment
  useEffect(() => {
    if (!volumeRef.current) return;
    if (visibility.volume && candles.length > 0) {
      const seen = new Set<number>();
      const data = candles
        .map((c) => ({
          time: toUTC(c.open_time),
          value: c.volume,
          color: c.close >= c.open ? 'rgba(38,166,154,0.45)' : 'rgba(239,83,80,0.45)',
        }))
        .filter(({ time }) => {
          const t = time as number;
          if (seen.has(t)) return false;
          seen.add(t);
          return true;
        })
        .sort((a, b) => (a.time as number) - (b.time as number));
      volumeRef.current.setData(data);
      chartRef.current?.priceScale('right').applyOptions({ scaleMargins: { top: 0, bottom: 0.2 } });
    } else {
      volumeRef.current.setData([]);
      chartRef.current?.priceScale('right').applyOptions({ scaleMargins: { top: 0, bottom: 0 } });
    }
  }, [candles, visibility.volume]);

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

    // Turtle System entry/exit markers
    if (turtleData) {
      for (const sig of turtleData.signals) {
        const isS1 = sig.system === 1;
        const isEntry = sig.type === 'entry_long' || sig.type === 'entry_short';
        const isLong = sig.type === 'entry_long' || sig.type === 'exit_long';
        const show = (isS1 && visibility.turtle_s1) || (!isS1 && visibility.turtle_s2);
        if (!show) continue;
        allMarkers.push({
          time: toUTC(sig.time),
          position: isLong ? ('belowBar' as const) : ('aboveBar' as const),
          color: isS1 ? 'rgba(34,197,94,0.9)' : 'rgba(96,165,250,0.9)',
          shape: isEntry
            ? (isLong ? ('arrowUp' as const) : ('arrowDown' as const))
            : ('circle' as const),
          size: 1 as const,
          text: `S${sig.system}${isEntry ? (isLong ? '▲' : '▼') : '×'}`,
        });
      }
    }

    // MA crossover markers
    const showCross2050 = visibility.ma20 && visibility.ma50;
    const showCross50200 = visibility.ma50 && visibility.ma200;
    if (showCross2050 || showCross50200) {
      const cs = candles; // candlesRef.current in overlay effect scope
      const smaArr = (period: number): number[] => {
        const out = new Array(cs.length).fill(NaN) as number[];
        let sum = 0;
        for (let i = 0; i < cs.length; i++) {
          sum += cs[i].close;
          if (i >= period) sum -= cs[i - period].close;
          if (i >= period - 1) out[i] = sum / period;
        }
        return out;
      };
      const ma20arr = showCross2050 ? smaArr(20) : [];
      const ma50arr = (showCross2050 || showCross50200) ? smaArr(50) : [];
      const ma200arr = showCross50200 ? smaArr(200) : [];

      for (let i = 1; i < cs.length; i++) {
        const t = toUTC(cs[i].open_time);
        if (showCross2050 && !isNaN(ma20arr[i - 1]) && !isNaN(ma20arr[i])) {
          const wasBelow = ma20arr[i - 1] < ma50arr[i - 1];
          const isAbove = ma20arr[i] >= ma50arr[i];
          if (wasBelow && isAbove) {
            allMarkers.push({ time: t, position: 'belowBar', color: '#f59e0b', shape: 'circle', size: 1, text: '20×50↑' });
          } else if (!wasBelow && !isAbove) {
            allMarkers.push({ time: t, position: 'aboveBar', color: '#3b82f6', shape: 'circle', size: 1, text: '20×50↓' });
          }
        }
        if (showCross50200 && !isNaN(ma50arr[i - 1]) && !isNaN(ma200arr[i - 1])) {
          const wasBelow = ma50arr[i - 1] < ma200arr[i - 1];
          const isAbove = ma50arr[i] >= ma200arr[i];
          if (wasBelow && isAbove) {
            allMarkers.push({ time: t, position: 'belowBar', color: '#FFD700', shape: 'arrowUp', size: 2, text: 'GX' });
          } else if (!wasBelow && !isAbove) {
            allMarkers.push({ time: t, position: 'aboveBar', color: '#ef4444', shape: 'arrowDown', size: 2, text: 'DX' });
          }
        }
      }
    }

    if (allMarkers.length > 0) {
      allMarkers.sort((a, b) => (a.time as number) - (b.time as number));
      markersPluginRef.current = createSeriesMarkers<Time>(series, allMarkers);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fvgs, ifvgs, bprs, liquidities, sweeps, killzones, po3s, htfBprs, visibility, trades, turtleData]);

  // Update Donchian channel series data when turtleData or visibility changes
  useEffect(() => {
    const toLine = (pts: DonchianPoint[]) =>
      pts.map((p) => ({ time: toUTC(p.time), value: p.value }));

    if (s1UpperRef.current) {
      const data = turtleData && visibility.turtle_s1 ? toLine(turtleData.s1_upper) : [];
      s1UpperRef.current.setData(data);
    }
    if (s1LowerRef.current) {
      const data = turtleData && visibility.turtle_s1 ? toLine(turtleData.s1_lower) : [];
      s1LowerRef.current.setData(data);
    }
    if (s2UpperRef.current) {
      const data = turtleData && visibility.turtle_s2 ? toLine(turtleData.s2_upper) : [];
      s2UpperRef.current.setData(data);
    }
    if (s2LowerRef.current) {
      const data = turtleData && visibility.turtle_s2 ? toLine(turtleData.s2_lower) : [];
      s2LowerRef.current.setData(data);
    }
  }, [turtleData, visibility.turtle_s1, visibility.turtle_s2]);

  // Recompute MA series whenever candles or MA visibility changes
  useEffect(() => {
    type LP = { time: ReturnType<typeof toUTC>; value: number };
    // lightweight-charts requires strictly ascending unique timestamps
    const dedup = (arr: LP[]): LP[] => {
      arr.sort((a, b) => (a.time as number) - (b.time as number));
      const seen = new Set<number>();
      return arr.filter(({ time }) => {
        const t = time as number;
        if (seen.has(t)) return false;
        seen.add(t);
        return true;
      });
    };

    const sma = (period: number): LP[] => {
      const result: LP[] = [];
      let sum = 0;
      for (let i = 0; i < candles.length; i++) {
        sum += candles[i].close;
        if (i >= period) sum -= candles[i - period].close;
        if (i >= period - 1) result.push({ time: toUTC(candles[i].open_time), value: sum / period });
      }
      return dedup(result);
    };

    if (ma20Ref.current) ma20Ref.current.setData(visibility.ma20 && candles.length >= 20 ? sma(20) : []);
    if (ma50Ref.current) ma50Ref.current.setData(visibility.ma50 && candles.length >= 50 ? sma(50) : []);
    if (ma200Ref.current) ma200Ref.current.setData(visibility.ma200 && candles.length >= 200 ? sma(200) : []);

    if (ema50Ref.current) {
      if (visibility.ema50 && candles.length >= 50) {
        const k = 2 / 51;
        let seed = 0;
        for (let i = 0; i < 50; i++) seed += candles[i].close;
        let prev = seed / 50;
        const emaData: LP[] = [{ time: toUTC(candles[49].open_time), value: prev }];
        for (let i = 50; i < candles.length; i++) {
          prev = candles[i].close * k + prev * (1 - k);
          emaData.push({ time: toUTC(candles[i].open_time), value: prev });
        }
        ema50Ref.current.setData(dedup(emaData));
      } else {
        ema50Ref.current.setData([]);
      }
    }

    if (vwapRef.current) {
      if (visibility.vwap && candles.length > 0) {
        const vwapData: LP[] = [];
        let cumTV = 0;
        let cumVol = 0;
        let currentDay = '';
        for (const c of candles) {
          const day = c.open_time.slice(0, 10);
          if (day !== currentDay) { cumTV = 0; cumVol = 0; currentDay = day; }
          const tp = (c.high + c.low + c.close) / 3;
          cumTV += tp * c.volume;
          cumVol += c.volume;
          vwapData.push({ time: toUTC(c.open_time), value: cumTV / cumVol });
        }
        vwapRef.current.setData(dedup(vwapData));
      } else {
        vwapRef.current.setData([]);
      }
    }
  }, [candles, visibility.ma20, visibility.ma50, visibility.ma200, visibility.ema50, visibility.vwap]);

  return (
    <div className="relative w-full">
      <button
        onClick={() => chartRef.current?.priceScale('right').applyOptions({ autoScale: true })}
        title="Auto scale Y-axis"
        style={{
          position: 'absolute',
          bottom: 40,
          right: 12,
          zIndex: 10,
          padding: '3px 7px',
          fontSize: 11,
          fontFamily: 'monospace',
          background: 'rgba(42,46,57,0.85)',
          color: '#d1d4dc',
          border: '1px solid #363c4e',
          borderRadius: 4,
          cursor: 'pointer',
          lineHeight: 1.4,
        }}
      >
        A
      </button>
      <div
        ref={tooltipRef}
        style={{
          display: 'none',
          position: 'absolute',
          top: 8,
          left: 12,
          zIndex: 10,
          fontSize: 12,
          fontFamily: 'monospace',
          background: 'rgba(19,23,34,0.85)',
          padding: '3px 8px',
          borderRadius: 4,
          pointerEvents: 'none',
          whiteSpace: 'nowrap',
        }}
      />
      <div
        ref={containerRef}
        className="w-full rounded-lg overflow-hidden border border-[#2a2e39]"
        style={{ height: 600 }}
      />
    </div>
  );
}
