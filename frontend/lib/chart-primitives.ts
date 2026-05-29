import type { IChartApi, ISeriesApi, SeriesType, UTCTimestamp } from 'lightweight-charts';

export interface Box {
  time1: UTCTimestamp;
  time2: UTCTimestamp;
  price1: number;
  price2: number;
  fillColor: string;
  borderColor?: string;
}

export interface KillZone {
  time1: UTCTimestamp;
  time2: UTCTimestamp;
  color: string;
}

// Scope type from fancy-canvas (accessed via useBitmapCoordinateSpace)
type BitmapScope = {
  context: CanvasRenderingContext2D;
  horizontalPixelRatio: number;
  verticalPixelRatio: number;
  bitmapSize: { width: number; height: number };
};

type Target = { useBitmapCoordinateSpace: (fn: (scope: BitmapScope) => void) => void };

class BoxRenderer {
  constructor(
    private _chart: IChartApi,
    private _series: ISeriesApi<SeriesType>,
    private _boxes: Box[],
  ) {}

  draw(target: Target): void {
    target.useBitmapCoordinateSpace(({ context: ctx, horizontalPixelRatio: hpr, verticalPixelRatio: vpr }) => {
      for (const box of this._boxes) {
        const x1 = this._chart.timeScale().timeToCoordinate(box.time1);
        const x2 = this._chart.timeScale().timeToCoordinate(box.time2);
        const y1 = this._series.priceToCoordinate(box.price1);
        const y2 = this._series.priceToCoordinate(box.price2);
        if (x1 === null || x2 === null || y1 === null || y2 === null) continue;

        const bx1 = Math.round(Math.min(x1, x2) * hpr);
        const bx2 = Math.round(Math.max(x1, x2) * hpr);
        const by1 = Math.round(Math.min(y1, y2) * vpr);
        const by2 = Math.round(Math.max(y1, y2) * vpr);
        const w = bx2 - bx1;
        const h = by2 - by1;
        if (w <= 0 || h <= 0) continue;

        ctx.fillStyle = box.fillColor;
        ctx.fillRect(bx1, by1, w, h);

        if (box.borderColor) {
          ctx.strokeStyle = box.borderColor;
          ctx.lineWidth = 1;
          ctx.strokeRect(bx1 + 0.5, by1 + 0.5, w - 1, h - 1);
        }
      }
    });
  }
}

class BoxPaneView {
  constructor(
    private _chart: IChartApi,
    private _series: ISeriesApi<SeriesType>,
    private _boxes: Box[],
  ) {}

  zOrder(): 'normal' {
    return 'normal';
  }

  renderer() {
    return new BoxRenderer(this._chart, this._series, this._boxes);
  }
}

export class BoxesPrimitive {
  constructor(
    private _chart: IChartApi,
    private _series: ISeriesApi<SeriesType>,
    private _boxes: Box[],
  ) {}

  updateAllViews(): void {}

  paneViews() {
    return [new BoxPaneView(this._chart, this._series, this._boxes)];
  }
}

class KillZoneRenderer {
  constructor(
    private _chart: IChartApi,
    private _zones: KillZone[],
  ) {}

  draw(_target: Target): void {}

  drawBackground(target: Target): void {
    target.useBitmapCoordinateSpace(({ context: ctx, horizontalPixelRatio: hpr, bitmapSize }) => {
      for (const zone of this._zones) {
        const x1 = this._chart.timeScale().timeToCoordinate(zone.time1);
        const x2 = this._chart.timeScale().timeToCoordinate(zone.time2);
        if (x1 === null || x2 === null) continue;

        const bx1 = Math.round(Math.min(x1, x2) * hpr);
        const bx2 = Math.round(Math.max(x1, x2) * hpr);
        if (bx2 - bx1 <= 0) continue;

        ctx.fillStyle = zone.color;
        ctx.fillRect(bx1, 0, bx2 - bx1, bitmapSize.height);
      }
    });
  }
}

class KillZonePaneView {
  constructor(
    private _chart: IChartApi,
    private _zones: KillZone[],
  ) {}

  zOrder(): 'bottom' {
    return 'bottom';
  }

  renderer() {
    return new KillZoneRenderer(this._chart, this._zones);
  }
}

export class KillZonePrimitive {
  constructor(
    private _chart: IChartApi,
    private _zones: KillZone[],
  ) {}

  updateAllViews(): void {}

  paneViews() {
    return [new KillZonePaneView(this._chart, this._zones)];
  }
}

const KST_OFFSET_S = 9 * 3600; // UTC+9 — shift all chart timestamps to KST display

export function toUTC(iso: string): UTCTimestamp {
  return ((new Date(iso).getTime() / 1000) + KST_OFFSET_S) as UTCTimestamp;
}

export const KZ_COLORS: Record<string, string> = {
  Asia: 'rgba(99,102,241,0.08)',
  London: 'rgba(59,130,246,0.08)',
  NY_AM: 'rgba(234,179,8,0.08)',
  NY_PM: 'rgba(249,115,22,0.08)',
};
