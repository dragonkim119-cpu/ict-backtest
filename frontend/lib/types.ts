export type Candle = {
  open_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type FVG = {
  type: 'bull' | 'bear';
  bottom: number;
  top: number;
  start_index: number;
  middle_index: number;
  end_index: number;
  created_time: string;
  mitigated: boolean;
  mitigated_time: string | null;
  invalidated: boolean;
  invalidated_time: string | null;
};

export type IFVG = {
  type: 'bull' | 'bear';
  bottom: number;
  top: number;
  created_time: string;
  original_fvg_created_time: string;
};

export type LiquidityPool = {
  side: 'BSL' | 'SSL';
  level: number;
  swing_times: string[];
  swept: boolean;
  swept_time: string | null;
};

export type Sweep = {
  type: 'bull' | 'bear';
  pool_level: number;
  sweep_index: number;
  sweep_time: string;
  sweep_extreme: number;
};

export type BPR = {
  type: 'bull' | 'bear';
  top: number;
  bottom: number;
  fvg_old_time: string;
  fvg_new_time: string;
  created_time: string;
  created_index: number;
};

export type KillZoneSpan = {
  name: 'Asia' | 'London' | 'NY_AM' | 'NY_PM';
  start_time: string;
  end_time: string;
};

export type Swing = {
  index: number;
  type: 'high' | 'low';
  price: number;
  time: string;
};

export type EntrySignal = {
  bpr: BPR;
  trigger_candle_index: number;
  trigger_candle_time: string;
  entry_index: number;
  entry_time: string;
  entry_price: number;
  direction: 'long' | 'short';
};

export type Trade = {
  entry: EntrySignal;
  sl: number;
  tp: number;
  exit_index: number;
  exit_time: string;
  exit_price: number;
  status: 'closed_win' | 'closed_loss' | 'closed_timeout';
  pnl_r: number;
};

export type Metrics = {
  total_trades: number;
  wins: number;
  losses: number;
  timeouts: number;
  win_rate: number;
  profit_factor: number;
  expectancy: number;
  total_pnl_r: number;
  max_drawdown_r: number;
  max_consecutive_losses: number;
  avg_trade_duration_candles: number;
};

export type PO3 = {
  session: 'London' | 'NY_AM';
  type: 'bull' | 'bear';
  accum_start_time: string;
  accum_end_time: string;
  accum_high: number;
  accum_low: number;
  manip_time: string;
  manip_extreme: number;
  distrib_start_time: string;
  distrib_end_time: string | null;
};

export type BacktestResponse = {
  run_id: string;
  symbol: string;
  interval: string;
  trades: Trade[];
  metrics: Metrics;
};

export type CandlesResponse = {
  symbol: string;
  interval: string;
  candles: Candle[];
};

export type PatternsResponse = {
  symbol: string;
  interval: string;
  swings: Swing[];
  fvgs: FVG[];
  ifvgs: IFVG[];
  bprs: BPR[];
  liquidities: LiquidityPool[];
  sweeps: Sweep[];
  killzones: KillZoneSpan[];
  po3s: PO3[];
};
