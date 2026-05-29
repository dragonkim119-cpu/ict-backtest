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

export type StoredTrade = {
  entry_index: number;
  entry_time: string;
  entry_price: number;
  direction: 'long' | 'short';
  sl: number;
  tp: number;
  exit_index: number;
  exit_time: string;
  exit_price: number;
  status: 'closed_win' | 'closed_loss' | 'closed_timeout';
  pnl_r: number;
};

export type BacktestRun = {
  run_id: string;
  symbol: string;
  interval: string;
  start_time: string | null;
  end_time: string | null;
  params_hash: string;
  params_json: string;
  total_trades: number;
  wins: number;
  losses: number;
  timeouts: number;
  win_rate: number;
  profit_factor: number | null;
  expectancy: number;
  total_pnl_r: number;
  max_drawdown_r: number;
  max_consecutive_losses: number;
  avg_trade_duration_candles: number;
  created_at: string;
};

export type RunDetailResponse = {
  run: BacktestRun;
  trades: StoredTrade[];
};

export type CheckItem = {
  id: number;
  label: string;
  passed: boolean;
  detail: string;
};

export type ChecklistResult = {
  symbol: string;
  interval: string;
  htf_interval: string;
  evaluated_at: string;
  price: number;
  checks: CheckItem[];
  score: number;
};

export type JournalEntry = {
  id: number;
  symbol: string;
  interval: string;
  direction: 'long' | 'short';
  entry_time: string;
  exit_time: string | null;
  entry_price: number;
  exit_price: number | null;
  sl: number | null;
  tp: number | null;
  result_pnl: number | null;
  rr: number | null;
  notes: string;
  tags: string[];
  run_id: string | null;
  created_at: string;
};

export type JournalEntryCreate = {
  symbol?: string;
  interval: string;
  direction: 'long' | 'short';
  entry_time: string;
  exit_time?: string | null;
  entry_price: number;
  exit_price?: number | null;
  sl?: number | null;
  tp?: number | null;
  result_pnl?: number | null;
  rr?: number | null;
  notes?: string;
  tags?: string[];
  run_id?: string | null;
};

export type JournalEntryUpdate = {
  exit_time?: string | null;
  exit_price?: number | null;
  sl?: number | null;
  tp?: number | null;
  result_pnl?: number | null;
  rr?: number | null;
  notes?: string | null;
  tags?: string[] | null;
  run_id?: string | null;
};

export type JournalCompareResult = {
  journal: JournalEntry;
  run: BacktestRun | null;
  trades: StoredTrade[] | null;
};

export type WeekdayStat = { day: string; total: number; wins: number; win_rate: number };
export type HourStat = { hour: number; total: number; wins: number; win_rate: number };
export type MonthStat = { month: string; total: number; wins: number; pnl_r: number };
export type DirectionStat = { direction: string; total: number; wins: number; win_rate: number; avg_pnl_r: number | null };
export type IntervalStat = { interval: string; total: number; wins: number; win_rate: number };

export type JournalStats = {
  closed_total: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_rr: number | null;
  total_pnl_r: number;
  by_weekday: WeekdayStat[];
  by_hour: HourStat[];
  by_month: MonthStat[];
  by_direction: DirectionStat[];
  by_interval: IntervalStat[];
};

export type BacktestAggregate = {
  total_runs: number;
  avg_win_rate: number | null;
  avg_profit_factor: number | null;
  avg_total_pnl_r: number | null;
};

export type JournalVsBacktest = {
  journal: JournalStats;
  backtest: BacktestAggregate;
};

export type BacktestResponse = {
  run_id: string;
  symbol: string;
  interval: string;
  trades: Trade[];
  metrics: Metrics;
  htf_bprs: BPR[];
};

export type CandleRangeResponse = {
  symbol: string;
  interval: string;
  start: string;
  end: string;
  count: number;
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
