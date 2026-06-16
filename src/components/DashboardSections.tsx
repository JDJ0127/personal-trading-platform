import {
  type Candidate,
  type NavItem,
} from "../data/mockData";
import backtestResult from "../data/backtestResult.json";
import rawStabilityReport from "../data/stabilityReport.json";
import rawDataStatus from "../data/dataStatus.json";
import rawStockPool from "../data/stockPool.json";
import rawSignalReport from "../data/signalReport.json";
import rawMarketRisk from "../data/marketRisk.json";
import rawSimulationReport from "../data/simulationReport.json";
import rawSimulationAccount from "../data/simulationAccount.json";
import rawRunLog from "../data/runLog.json";
import rawNewsReport from "../data/newsReport.json";
import rawReplayMarketRisk from "../data/paperReplay/marketRisk.json";
import rawReplaySimulationReport from "../data/paperReplay/simulationReport.json";
import rawReplaySimulationAccount from "../data/paperReplay/simulationAccount.json";
import rawReplayRunLog from "../data/paperReplay/runLog.json";

type DashboardSectionsProps = {
  activeItem: NavItem;
};

type DataStatusReport = {
  schemaVersion: number;
  generatedAt: string;
  database: string;
  summary: {
    latestTradeDate: string;
    latestCalendarDate: string;
    tableCount: number;
    totalRecords: number;
    qualityIssueCount: number;
    stockCount?: number;
    barStockCount?: number;
    barTradeDayCount?: number;
    expectedBarCount?: number;
    actualBarCount?: number;
    missingBarCount?: number;
    coverageRate?: number;
  };
  coverage?: {
    startDate: string;
    endDate: string;
    stockCount: number;
    barStockCount: number;
    calendarTradeDayCount: number;
    barTradeDayCount: number;
    expectedBarCount: number;
    actualBarCount: number;
    missingBarCount: number;
    coverageRate: number;
    missingByDate: Array<{
      tradeDate: string;
      missingCount: number;
      missingCodes: string[];
    }>;
    missingByStock: Array<{
      tsCode: string;
      missingCount: number;
    }>;
  };
  tables: Array<{
    table: string;
    name: string;
    source: string;
    status: string;
    latestDate: string;
    recordCount: number;
  }>;
  qualityIssues: Array<{
    table: string;
    key: string;
    message: string;
  }>;
};

const dataStatus = rawDataStatus as DataStatusReport;
const dataCoverage = dataStatus.coverage ?? {
  startDate: "--",
  endDate: "--",
  stockCount: dataStatus.summary.stockCount ?? 0,
  barStockCount: dataStatus.summary.barStockCount ?? 0,
  calendarTradeDayCount: 0,
  barTradeDayCount: dataStatus.summary.barTradeDayCount ?? 0,
  expectedBarCount: dataStatus.summary.expectedBarCount ?? 0,
  actualBarCount: dataStatus.summary.actualBarCount ?? 0,
  missingBarCount: dataStatus.summary.missingBarCount ?? 0,
  coverageRate: dataStatus.summary.coverageRate ?? 0,
  missingByDate: [],
  missingByStock: [],
};

type StockPoolReport = {
  schemaVersion: number;
  tradeDate: string;
  summary: {
    total: number;
    passed: number;
    blocked: number;
    passRate: number;
  };
  filters: Array<{
    reason: string;
    count: number;
  }>;
  stocks: Array<{
    tsCode: string;
    name: string;
    industry: string;
    isPass: boolean;
    filterReasons: string[];
    listedDays: number;
    close: number | null;
    amount: number | null;
    avgAmount: number | null;
  }>;
};

const stockPool = rawStockPool as StockPoolReport;

type SignalReport = {
  schemaVersion: number;
  tradeDate: string;
  summary: {
    signalCount: number;
    buyCount: number;
    watchCount: number;
  };
  signals: Array<{
    tsCode: string;
    name: string;
    industry: string;
    signal: "buy" | "watch";
    totalScore: number;
    trendScore: number;
    strengthScore: number;
    volumeScore: number;
    riskScore: number;
    targetWeight: number;
    reason: string;
  }>;
};

const signalReport = rawSignalReport as SignalReport;

type MarketRiskReport = {
  tradeDate: string;
  market: {
    score: number;
    state: string;
    maxWeight: number;
    breadthUpPct: number;
    upCount: number;
    downCount: number;
    newHighCount: number;
    newLowCount: number;
    trendPassPct: number;
    checks: Array<{ name: string; passed: boolean }>;
  };
  risk: {
    state: string;
    allowedPositionWeight: number;
    maxDrawdownLimit: number;
    currentDrawdown: number;
    actions: string[];
  };
};

const marketRisk = rawMarketRisk as MarketRiskReport;

type SimulationReport = {
  tradeDate: string;
  account: {
    initialCash: number;
    maxPositions: number;
    maxPortfolioWeight: number;
    currentTotalAsset: number;
    currentCash: number;
    currentWeight: number;
  };
  risk: {
    state: string;
    allowedPositionWeight: number;
    maxDrawdownLimit: number;
    currentDrawdown: number;
    actions: string[];
  };
  summary: { signalCount: number; plannedOrderCount: number; blockedOrderCount: number; watchCount: number };
  orders: Array<{
    tradeDate: string;
    tsCode: string;
    side: string;
    targetWeight: number;
    score: number;
    status: string;
    blockReason: string;
    orderQuantity: number;
    orderPrice: number | null;
    estimatedAmount: number;
    upLimit: number | null;
    downLimit: number | null;
  }>;
  checks: string[];
};

const simulationReport = rawSimulationReport as SimulationReport;

type SimulationAccountReport = {
  account: {
    accountId: string;
    accountName: string;
    mode: string;
    strategyName: string;
    initialCash: number;
    totalAsset: number;
    cash: number;
    marketValue: number;
    cumulativeReturn: number;
    maxDrawdown: number;
    positionCount: number;
    lastTradeDate: string;
    status: string;
  };
  positions: Array<{
    tradeDate: string;
    tsCode: string;
    name: string;
    industry: string;
    quantity: number;
    availableQuantity: number;
    costPrice: number;
    marketPrice: number;
    marketValue: number;
    weight: number;
    unrealizedPnl: number;
    unrealizedPnlPct: number;
    stopPrice: number;
    holdingDays: number;
  }>;
  equityCurve: Array<{
    tradeDate: string;
    totalAsset: number;
    cash: number;
    marketValue: number;
    dailyReturn: number;
    cumulativeReturn: number;
    drawdown: number;
    maxDrawdown: number;
    positionCount: number;
    totalWeight: number;
  }>;
  orders: Array<{
    orderId: string;
    tradeDate: string;
    tsCode: string;
    side: string;
    orderPrice: number;
    orderQuantity: number;
    filledQuantity: number;
    avgFillPrice: number;
    status: string;
    rejectReason: string;
  }>;
  fills: Array<{
    fillId: string;
    tradeDate: string;
    tsCode: string;
    side: string;
    quantity: number;
    price: number;
    commission: number;
    stampTax: number;
    transferFee: number;
    fee: number;
  }>;
  summary: { orderCount: number; fillCount: number; positionCount: number; equityPointCount: number };
};

const simulationAccount = rawSimulationAccount as SimulationAccountReport;
const replayMarketRisk = rawReplayMarketRisk as MarketRiskReport;
const replaySimulationReport = rawReplaySimulationReport as SimulationReport;
const replaySimulationAccount = rawReplaySimulationAccount as SimulationAccountReport;

type RunLogReport = {
  summary: {
    runCount: number;
    successCount: number;
    failedCount: number;
    runningCount: number;
    latestStatus: string;
    latestTradeDate: string;
  };
  runs: Array<{
    runId: string;
    workflow: string;
    source: string;
    accountId: string | null;
    tradeDate: string | null;
    status: string;
    startedAt: string;
    finishedAt: string | null;
    durationMs: number | null;
    stockCount: number;
    signalCount: number;
    plannedOrderCount: number;
    blockedOrderCount: number;
    orderCount: number;
    fillCount: number;
    errorMessage: string;
  }>;
};

const runLog = rawRunLog as RunLogReport;
const replayRunLog = rawReplayRunLog as RunLogReport;

type NewsReport = {
  summary: { eventCount: number; positiveCount: number; negativeCount: number; highImportanceCount: number };
  events: Array<{
    eventId: string;
    time: string;
    source: string;
    title: string;
    eventType: string;
    sentiment: string;
    importance: number;
    sector: string;
    passCount: number;
    reason: string;
  }>;
};

const newsReport = rawNewsReport as NewsReport;

type StabilityReport = {
  strategy: string;
  period: { start: string; end: string; tradingDays: number };
  summary: {
    cumulativeReturn: number;
    maxDrawdown: number;
    winRate: number;
    orderCount: number;
    fillCount: number;
    winningMonthCount: number;
    losingMonthCount: number;
    monthlyWinRate: number;
    bestMonthReturn: number;
    worstMonthReturn: number;
    maxConsecutiveLosingMonths: number;
  };
  yearlyReturns: Array<{ period: string; startAsset: number; endAsset: number; return: number; maxDrawdown: number; tradingDays: number }>;
  monthlyReturns: Array<{ period: string; startAsset: number; endAsset: number; return: number; maxDrawdown: number; tradingDays: number }>;
  checks: Array<{ name: string; passed: boolean }>;
};

const stabilityReport = rawStabilityReport as StabilityReport;

const currencyFormatter = new Intl.NumberFormat("zh-CN", {
  style: "currency",
  currency: "CNY",
  maximumFractionDigits: 0,
});

const moneyFormatter = new Intl.NumberFormat("zh-CN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function signedRatioPct(value: number) {
  return `${value > 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;
}

function ratioPct(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}

function money(value: number) {
  return moneyFormatter.format(value);
}

function compactMoney(value: number | null) {
  if (value === null) return "--";
  if (value >= 100_000_000) return `${(value / 100_000_000).toFixed(2)} 亿`;
  if (value >= 10_000) return `${(value / 10_000).toFixed(0)} 万`;
  return money(value);
}

function duration(value: number | null) {
  if (value === null) return "--";
  if (value < 1000) return `${value} ms`;
  return `${(value / 1000).toFixed(1)} s`;
}

function trendClass(value: number) {
  if (value > 0) return "up";
  if (value < 0) return "down";
  return "flat";
}

function toneClass(value: string): "up" | "down" | "flat" {
  if (value === "up" || value === "down") return value;
  return "flat";
}

function PageHeader({ title, description }: { title: string; description: string }) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <span className="status-pill">MVP 原型</span>
    </div>
  );
}

function StatCard({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: "up" | "down" | "flat" }) {
  return (
    <section className="stat-card">
      <div className="stat-label">{label}</div>
      <div className={tone ? `stat-value ${tone}` : "stat-value"}>{value}</div>
      {hint ? <div className="stat-hint">{hint}</div> : null}
    </section>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="score-row">
      <span>{label}</span>
      <div className="score-track">
        <div className="score-fill" style={{ width: `${value}%` }} />
      </div>
      <strong>{value}</strong>
    </div>
  );
}

function SignalTag({ signal }: { signal: Candidate["signal"] }) {
  const label = {
    buy: "买入",
    sell: "卖出",
    hold: "持有",
    watch: "观察",
  }[signal];

  return <span className={`signal-tag ${signal}`}>{label}</span>;
}

const latestEquityPoint = backtestResult.equityCurve.at(-1);
const latestDrawdownPoint = backtestResult.drawdownCurve.at(-1);

const homeAccountSummary = {
  totalAsset: latestEquityPoint?.totalAsset ?? backtestResult.metrics.finalAsset,
  cash: latestEquityPoint?.cash ?? 0,
  marketValue: latestEquityPoint?.marketValue ?? 0,
  dailyReturn: latestEquityPoint?.dailyReturn ?? 0,
  cumulativeReturn: backtestResult.metrics.cumulativeReturn,
  currentDrawdown: latestDrawdownPoint?.drawdown ?? backtestResult.metrics.maxDrawdown,
  maxDrawdown: backtestResult.metrics.maxDrawdown,
  totalWeight: latestEquityPoint?.totalWeight ?? 0,
  positionCount: latestEquityPoint?.positionCount ?? 0,
};

type AccountSummary = {
  totalAsset: number;
  cash: number;
  marketValue: number;
  dailyReturn: number;
  cumulativeReturn: number;
  currentDrawdown: number;
  maxDrawdown: number;
  totalWeight: number;
  positionCount: number;
};

const latestReplayEquity = replaySimulationAccount.equityCurve.at(-1);

function buildAccountSummary(accountReport: SimulationAccountReport): AccountSummary {
  const latestPoint = accountReport.equityCurve.at(-1);
  return {
    totalAsset: accountReport.account.totalAsset,
    cash: accountReport.account.cash,
    marketValue: accountReport.account.marketValue,
    dailyReturn: latestPoint?.dailyReturn ?? 0,
    cumulativeReturn: accountReport.account.cumulativeReturn,
    currentDrawdown: latestPoint?.drawdown ?? accountReport.account.maxDrawdown,
    maxDrawdown: accountReport.account.maxDrawdown,
    totalWeight: accountReport.account.totalAsset > 0 ? accountReport.account.marketValue / accountReport.account.totalAsset : 0,
    positionCount: accountReport.account.positionCount,
  };
}

const simulationAccountSummary = buildAccountSummary(simulationAccount);
const replayAccountSummary = buildAccountSummary(replaySimulationAccount);

const simulationIndustryExposure = (() => {
  return buildIndustryExposure(simulationAccount);
})();

function buildIndustryExposure(accountReport: SimulationAccountReport) {
  const exposure = new Map<string, { industry: string; weight: number; count: number }>();
  for (const position of accountReport.positions) {
    const current = exposure.get(position.industry) ?? { industry: position.industry, weight: 0, count: 0 };
    current.weight += position.weight;
    current.count += 1;
    exposure.set(position.industry, current);
  }
  const rows = Array.from(exposure.values());
  const cashWeight = Math.max(0, 1 - rows.reduce((sum, item) => sum + item.weight, 0));
  rows.push({ industry: "现金", weight: cashWeight, count: 0 });
  return rows.sort((a, b) => b.weight - a.weight);
}

const replayIndustryExposure = buildIndustryExposure(replaySimulationAccount);

const homeSignalRows: Candidate[] = signalReport.signals.map((item) => ({
  code: item.tsCode,
  name: item.name,
  industry: item.industry,
  totalScore: item.totalScore,
  trendScore: item.trendScore,
  strengthScore: item.strengthScore,
  volumeScore: item.volumeScore,
  industryScore: 0,
  riskScore: item.riskScore,
  signal: item.signal,
  targetWeight: item.targetWeight * 100,
  reason: item.reason,
}));

function TradeSideTag({ side }: { side: string }) {
  const label = side === "buy" ? "买入" : side === "sell" ? "卖出" : "观察";
  const className = side === "buy" ? "buy" : side === "sell" ? "sell" : "watch";
  return <span className={`signal-tag ${className}`}>{label}</span>;
}

function AccountStatGrid({
  summary = simulationAccountSummary,
  sourceHint = `模拟账户 ${simulationAccount.account.lastTradeDate ?? "--"}`,
}: {
  summary?: AccountSummary;
  sourceHint?: string;
}) {
  return (
    <div className="stat-grid">
      <StatCard label="总资产" value={currencyFormatter.format(summary.totalAsset)} hint={sourceHint} />
      <StatCard label="现金" value={currencyFormatter.format(summary.cash)} hint="账户现金" />
      <StatCard label="当前仓位" value={ratioPct(summary.totalWeight)} hint={`${summary.positionCount} 只持仓`} />
      <StatCard label="当前回撤" value={ratioPct(summary.currentDrawdown)} hint={`最大回撤 ${ratioPct(summary.maxDrawdown)}`} tone={summary.currentDrawdown > 0 ? "down" : "flat"} />
      <StatCard label="当日收益" value={signedRatioPct(summary.dailyReturn)} hint="最新净值日收益" tone={trendClass(summary.dailyReturn)} />
      <StatCard label="累计收益" value={signedRatioPct(summary.cumulativeReturn)} hint={`初始资金 ${currencyFormatter.format(backtestResult.metrics.initialCash)}`} tone={trendClass(summary.cumulativeReturn)} />
    </div>
  );
}

function CandidateTable({ rows = homeSignalRows }: { rows?: Candidate[] }) {
  if (rows.length === 0) {
    return <div className="empty-state">当前交易日没有策略候选信号。</div>;
  }

  return (
    <div className="table-card">
      <table>
        <thead>
          <tr>
            <th>代码</th>
            <th>名称</th>
            <th>行业</th>
            <th>综合分</th>
            <th>信号</th>
            <th>目标仓位</th>
            <th>原因</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((item) => (
            <tr key={`${item.code}-${item.signal}`}>
              <td>{item.code}</td>
              <td>{item.name}</td>
              <td>{item.industry}</td>
              <td>{item.totalScore}</td>
              <td><SignalTag signal={item.signal} /></td>
              <td>{item.targetWeight > 0 ? `${item.targetWeight}%` : "--"}</td>
              <td>{item.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PortfolioPositionTable({ accountReport = simulationAccount }: { accountReport?: SimulationAccountReport }) {
  if (accountReport.positions.length === 0) {
    return <div className="empty-state">当前模拟账户没有持仓。</div>;
  }

  return (
    <div className="table-card">
      <table>
        <thead>
          <tr>
            <th>代码</th>
            <th>名称</th>
            <th>行业</th>
            <th>数量</th>
            <th>可用</th>
            <th>成本价</th>
            <th>市价</th>
            <th>仓位</th>
            <th>浮盈亏</th>
            <th>止损价</th>
            <th>持仓天数</th>
          </tr>
        </thead>
        <tbody>
          {accountReport.positions.map((item) => (
            <tr key={item.tsCode}>
              <td>{item.tsCode}</td>
              <td>{item.name}</td>
              <td>{item.industry}</td>
              <td>{item.quantity}</td>
              <td>{item.availableQuantity}</td>
              <td>{money(item.costPrice)}</td>
              <td>{money(item.marketPrice)}</td>
              <td>{ratioPct(item.weight)}</td>
              <td className={trendClass(item.unrealizedPnlPct)}>{signedRatioPct(item.unrealizedPnlPct)}</td>
              <td>{money(item.stopPrice)}</td>
              <td>{item.holdingDays}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BacktestCurveChart() {
  const equityPoints = backtestResult.equityCurve;
  const drawdownPoints = backtestResult.drawdownCurve;
  const width = 100;
  const height = 100;
  const equityValues = equityPoints.map((point) => point.strategyNetValue);
  const minEquity = Math.min(...equityValues);
  const maxEquity = Math.max(...equityValues);
  const equityRange = Math.max(0.0001, maxEquity - minEquity);
  const maxDrawdown = Math.max(0.0001, ...drawdownPoints.map((point) => point.drawdown));

  const equityLine = equityPoints.map((point, index) => {
    const x = equityPoints.length === 1 ? 0 : (index / (equityPoints.length - 1)) * width;
    const y = height - ((point.strategyNetValue - minEquity) / equityRange) * 70 - 15;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ");

  const drawdownLine = drawdownPoints.map((point, index) => {
    const x = drawdownPoints.length === 1 ? 0 : (index / (drawdownPoints.length - 1)) * width;
    const y = 58 + (point.drawdown / maxDrawdown) * 28;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ");

  return (
    <div className="curve-chart" aria-label="回测净值和回撤曲线">
      <div className="chart-legend">
        <span><i className="legend-dot equity" />策略净值</span>
        <span><i className="legend-dot drawdown" />历史回撤</span>
      </div>
      <svg className="curve-svg" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" role="img">
        <line x1="0" x2="100" y1="15" y2="15" className="chart-grid-line" />
        <line x1="0" x2="100" y1="50" y2="50" className="chart-grid-line" />
        <line x1="0" x2="100" y1="85" y2="85" className="chart-grid-line" />
        <polyline points={equityLine} className="equity-line" />
        <polyline points={drawdownLine} className="drawdown-line" />
      </svg>
      <div className="chart-axis">
        <span>{equityPoints[0]?.date ?? "--"}</span>
        <span>净值 {equityPoints.at(-1)?.strategyNetValue.toFixed(4) ?? "--"}</span>
        <span>{equityPoints.at(-1)?.date ?? "--"}</span>
      </div>
    </div>
  );
}

function AccountCurveChart({ accountReport }: { accountReport: SimulationAccountReport }) {
  const equityPoints = accountReport.equityCurve;
  if (equityPoints.length === 0) {
    return <div className="empty-state">当前账户暂无权益曲线。</div>;
  }

  const width = 100;
  const height = 100;
  const initialCash = Math.max(0.0001, accountReport.account.initialCash);
  const latestPoint = equityPoints[equityPoints.length - 1];
  const netValues = equityPoints.map((point) => point.totalAsset / initialCash);
  const minNetValue = Math.min(...netValues);
  const maxNetValue = Math.max(...netValues);
  const netValueRange = Math.max(0.0001, maxNetValue - minNetValue);
  const maxDrawdown = Math.max(0.0001, ...equityPoints.map((point) => point.drawdown));

  const equityLine = equityPoints.map((point, index) => {
    const x = equityPoints.length === 1 ? 0 : (index / (equityPoints.length - 1)) * width;
    const netValue = point.totalAsset / initialCash;
    const y = height - ((netValue - minNetValue) / netValueRange) * 70 - 15;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ");

  const drawdownLine = equityPoints.map((point, index) => {
    const x = equityPoints.length === 1 ? 0 : (index / (equityPoints.length - 1)) * width;
    const y = 58 + (point.drawdown / maxDrawdown) * 28;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ");

  return (
    <div className="curve-chart" aria-label="模拟账户净值和回撤曲线">
      <div className="chart-legend">
        <span><i className="legend-dot equity" />账户净值</span>
        <span><i className="legend-dot drawdown" />账户回撤</span>
      </div>
      <svg className="curve-svg" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" role="img">
        <line x1="0" x2="100" y1="15" y2="15" className="chart-grid-line" />
        <line x1="0" x2="100" y1="50" y2="50" className="chart-grid-line" />
        <line x1="0" x2="100" y1="85" y2="85" className="chart-grid-line" />
        <polyline points={equityLine} className="equity-line" />
        <polyline points={drawdownLine} className="drawdown-line" />
      </svg>
      <div className="chart-axis">
        <span>{equityPoints[0]?.tradeDate ?? "--"}</span>
        <span>净值 {(latestPoint.totalAsset / initialCash).toFixed(4)}</span>
        <span>{latestPoint.tradeDate}</span>
      </div>
    </div>
  );
}

function BacktestParameterGrid() {
  const params = backtestResult.parameters;
  const rows = [
    ["初始资金", currencyFormatter.format(params.initialCash)],
    ["最大回撤硬线", ratioPct(params.maxDrawdownLimit)],
    ["最大持仓数", `${params.maxPositions} 只`],
    ["单股仓位", `${ratioPct(params.minPositionWeight)} - ${ratioPct(params.maxPositionWeight)}`],
    ["组合仓位上限", ratioPct(params.maxPortfolioWeight)],
    ["买入单位", `${params.lotSize} 股`],
    ["佣金率", ratioPct(params.commissionRate)],
    ["最低佣金", `${money(params.minCommission)} 元`],
    ["印花税", ratioPct(params.stampTaxRate)],
    ["过户费", ratioPct(params.transferFeeRate)],
    ["滑点", `${params.slippageBps} bps`],
  ];

  return (
    <div className="parameter-grid">
      {rows.map(([label, value]) => (
        <div className="parameter-item" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

function BacktestOrderTable() {
  return (
    <div className="table-card">
      <table className="backtest-table">
        <thead>
          <tr>
            <th>交易日</th>
            <th>代码</th>
            <th>方向</th>
            <th>委托价</th>
            <th>委托数量</th>
            <th>成交数量</th>
            <th>均价</th>
            <th>状态</th>
            <th>拒单原因</th>
          </tr>
        </thead>
        <tbody>
          {backtestResult.orders.map((order) => (
            <tr key={order.orderId}>
              <td>{order.tradeDate}</td>
              <td>{order.tsCode}</td>
              <td><TradeSideTag side={order.side} /></td>
              <td>{money(order.orderPrice)}</td>
              <td>{order.orderQuantity}</td>
              <td>{order.filledQuantity}</td>
              <td>{money(order.avgFillPrice)}</td>
              <td>{order.status}</td>
              <td>{order.rejectReason || "--"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BacktestFillTable() {
  return (
    <div className="table-card">
      <table className="backtest-table">
        <thead>
          <tr>
            <th>交易日</th>
            <th>代码</th>
            <th>方向</th>
            <th>数量</th>
            <th>价格</th>
            <th>佣金</th>
            <th>印花税</th>
            <th>过户费</th>
            <th>费用合计</th>
          </tr>
        </thead>
        <tbody>
          {backtestResult.fills.map((fill) => (
            <tr key={`${fill.tradeDate}-${fill.tsCode}-${fill.side}-${fill.quantity}`}>
              <td>{fill.tradeDate}</td>
              <td>{fill.tsCode}</td>
              <td><TradeSideTag side={fill.side} /></td>
              <td>{fill.quantity}</td>
              <td>{money(fill.price)}</td>
              <td>{money(fill.commission)}</td>
              <td>{money(fill.stampTax)}</td>
              <td>{money(fill.transferFee)}</td>
              <td>{money(fill.fee)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SimulationAccountOrderTable({ accountReport = simulationAccount }: { accountReport?: SimulationAccountReport }) {
  if (accountReport.orders.length === 0) {
    return <div className="empty-state">模拟账户暂无已生成订单。</div>;
  }

  return (
    <div className="table-card">
      <table className="backtest-table">
        <thead>
          <tr>
            <th>交易日</th>
            <th>代码</th>
            <th>方向</th>
            <th>委托价</th>
            <th>委托数量</th>
            <th>成交数量</th>
            <th>均价</th>
            <th>状态</th>
            <th>拒单原因</th>
          </tr>
        </thead>
        <tbody>
          {accountReport.orders.map((order) => (
            <tr key={order.orderId}>
              <td>{order.tradeDate}</td>
              <td>{order.tsCode}</td>
              <td><TradeSideTag side={order.side} /></td>
              <td>{money(order.orderPrice)}</td>
              <td>{order.orderQuantity}</td>
              <td>{order.filledQuantity}</td>
              <td>{money(order.avgFillPrice)}</td>
              <td><span className={`status-chip ${order.status === "filled" ? "ok" : "pending"}`}>{order.status}</span></td>
              <td>{order.rejectReason || "--"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SimulationFillTable({ accountReport = simulationAccount }: { accountReport?: SimulationAccountReport }) {
  if (accountReport.fills.length === 0) {
    return <div className="empty-state">模拟账户暂无成交流水。</div>;
  }

  return (
    <div className="table-card">
      <table className="backtest-table">
        <thead>
          <tr>
            <th>成交日</th>
            <th>代码</th>
            <th>方向</th>
            <th>数量</th>
            <th>价格</th>
            <th>佣金</th>
            <th>印花税</th>
            <th>过户费</th>
            <th>费用合计</th>
          </tr>
        </thead>
        <tbody>
          {accountReport.fills.map((fill) => (
            <tr key={fill.fillId}>
              <td>{fill.tradeDate}</td>
              <td>{fill.tsCode}</td>
              <td><TradeSideTag side={fill.side} /></td>
              <td>{fill.quantity}</td>
              <td>{money(fill.price)}</td>
              <td>{money(fill.commission)}</td>
              <td>{money(fill.stampTax)}</td>
              <td>{money(fill.transferFee)}</td>
              <td>{money(fill.fee)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SimulationPlanTable({ report }: { report: SimulationReport }) {
  if (report.orders.length === 0) {
    return <div className="empty-state">当前没有可生成的模拟订单。</div>;
  }

  return (
    <div className="table-card">
      <table>
        <thead>
          <tr>
            <th>交易日</th>
            <th>代码</th>
            <th>方向</th>
            <th>分数</th>
            <th>目标仓位</th>
            <th>计划数量</th>
            <th>计划价</th>
            <th>预计金额</th>
            <th>状态</th>
            <th>阻断原因</th>
          </tr>
        </thead>
        <tbody>
          {report.orders.map((order) => (
            <tr key={`${order.tradeDate}-${order.tsCode}-${order.side}`}>
              <td>{order.tradeDate}</td>
              <td>{order.tsCode}</td>
              <td><TradeSideTag side={order.side} /></td>
              <td>{order.score.toFixed(1)}</td>
              <td>{ratioPct(order.targetWeight)}</td>
              <td>{order.orderQuantity}</td>
              <td>{order.orderPrice === null ? "--" : money(order.orderPrice)}</td>
              <td>{currencyFormatter.format(order.estimatedAmount)}</td>
              <td><span className={`status-chip ${order.status === "planned" ? "ok" : "pending"}`}>{order.status}</span></td>
              <td>{order.blockReason || "--"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StabilityPeriodTable({ rows }: { rows: StabilityReport["monthlyReturns"] }) {
  return (
    <div className="table-card">
      <table>
        <thead>
          <tr>
            <th>周期</th>
            <th>期初资产</th>
            <th>期末资产</th>
            <th>收益率</th>
            <th>最大回撤</th>
            <th>交易日数</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.period}>
              <td>{row.period}</td>
              <td>{currencyFormatter.format(row.startAsset)}</td>
              <td>{currencyFormatter.format(row.endAsset)}</td>
              <td className={trendClass(row.return)}>{signedRatioPct(row.return)}</td>
              <td>{ratioPct(row.maxDrawdown)}</td>
              <td>{row.tradingDays}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function HomeSection() {
  const latestTableStatus = dataStatus.summary.qualityIssueCount === 0 ? "正常" : "有异常";
  const homeStatusTone = dataStatus.summary.qualityIssueCount === 0 ? "ok" : "pending";

  return (
    <>
      <PageHeader title="首页总览" description={`交易日 ${dataStatus.summary.latestTradeDate} · 快速查看市场是否可做、账户风险是否安全、次日是否有交易动作。`} />
      <AccountStatGrid />
      <div className="two-column">
        <section className="panel">
          <h2>市场与风控</h2>
          <div className="summary-line">
            <span>市场评分</span>
            <strong>{marketRisk.market.score}/5 · {marketRisk.market.state}</strong>
          </div>
          <div className="summary-line">
            <span>允许最大仓位</span>
            <strong>{ratioPct(marketRisk.risk.allowedPositionWeight)}</strong>
          </div>
          <div className="summary-line">
            <span>风控状态</span>
            <strong>{marketRisk.risk.state}</strong>
          </div>
          <div className="summary-line">
            <span>当前仓位</span>
            <strong>{ratioPct(simulationAccountSummary.totalWeight)}</strong>
          </div>
        </section>
        <section className="panel">
          <h2>今日动作</h2>
          <div className="summary-line">
            <span>买入信号</span>
            <strong>{signalReport.summary.buyCount} 只</strong>
          </div>
          <div className="summary-line">
            <span>观察/计划</span>
            <strong>{simulationReport.summary.watchCount} / {simulationReport.summary.plannedOrderCount}</strong>
          </div>
          <div className="summary-line">
            <span>重要新闻</span>
            <strong>{newsReport.summary.highImportanceCount} 条</strong>
          </div>
          <div className="summary-line">
            <span>数据状态</span>
            <strong><span className={`status-chip ${homeStatusTone}`}>{latestTableStatus}</span></strong>
          </div>
        </section>
      </div>
      <section className="panel">
        <h2>策略观察池</h2>
        <CandidateTable rows={homeSignalRows.slice(0, 3)} />
      </section>
      <section className="panel">
        <h2>最新回测状态</h2>
        <div className="summary-grid">
          <div className="summary-line">
            <span>策略</span>
            <strong>{backtestResult.strategy.name}</strong>
          </div>
          <div className="summary-line">
            <span>订单/成交</span>
            <strong>{backtestResult.metrics.orderCount} / {backtestResult.metrics.fillCount}</strong>
          </div>
          <div className="summary-line">
            <span>总交易费用</span>
            <strong>{money(backtestResult.metrics.totalFee)} 元</strong>
          </div>
          <div className="summary-line">
            <span>数据记录</span>
            <strong>{dataStatus.summary.totalRecords.toLocaleString("zh-CN")} 条</strong>
          </div>
        </div>
      </section>
    </>
  );
}

function MarketSection() {
  return (
    <>
      <PageHeader title="市场环境" description={`交易日 ${marketRisk.tradeDate} · 展示市场评分、市场宽度、新高新低和仓位上限。`} />
      <div className="stat-grid compact">
        <StatCard label="市场评分" value={`${marketRisk.market.score}/5`} hint={marketRisk.market.state} />
        <StatCard label="组合最大仓位" value={ratioPct(marketRisk.market.maxWeight)} hint="由市场评分决定" />
        <StatCard label="上涨股票占比" value={`${marketRisk.market.breadthUpPct}%`} hint={`${marketRisk.market.upCount} 涨 / ${marketRisk.market.downCount} 跌`} tone={marketRisk.market.breadthUpPct > 55 ? "up" : "down"} />
        <StatCard label="短期新高/新低" value={`${marketRisk.market.newHighCount}/${marketRisk.market.newLowCount}`} hint="市场宽度辅助项" />
      </div>
      <section className="panel">
        <h2>评分条件</h2>
        <div className="check-grid">
          {marketRisk.market.checks.map((check) => (
            <div className="check-item" key={check.name}>
              <span className={check.passed ? "check-dot pass" : "check-dot fail"} />
              <span>{check.name}</span>
              <strong>{check.passed ? "+1" : "+0"}</strong>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

function UniverseSection() {
  return (
    <>
      <PageHeader title="股票池" description={`交易日 ${stockPool.tradeDate} · 基础过滤、流动性过滤和可交易股票池统计。`} />
      <div className="stat-grid compact">
        <StatCard label="全市场股票" value={stockPool.summary.total.toLocaleString("zh-CN")} />
        <StatCard label="可交易股票池" value={stockPool.summary.passed.toLocaleString("zh-CN")} />
        <StatCard label="过滤剔除" value={stockPool.summary.blocked.toLocaleString("zh-CN")} />
        <StatCard label="通过率" value={ratioPct(stockPool.summary.passRate)} />
      </div>
      <section className="panel">
        <h2>过滤原因统计</h2>
        {stockPool.filters.length === 0 ? (
          <div className="empty-state">当前交易日没有股票被基础过滤阻断。</div>
        ) : (
          <div className="filter-grid">
            {stockPool.filters.map((item) => (
              <div className="filter-item" key={item.reason}>
                <span>{item.reason}</span>
                <strong>{item.count}</strong>
              </div>
            ))}
          </div>
        )}
      </section>
      <section className="panel">
        <h2>股票池列表</h2>
        <div className="table-card">
          <table>
            <thead>
              <tr>
                <th>代码</th>
                <th>名称</th>
                <th>市场</th>
                <th>状态</th>
                <th>过滤原因</th>
                <th>上市天数</th>
                <th>收盘价</th>
                <th>成交额</th>
                <th>均额</th>
              </tr>
            </thead>
            <tbody>
              {stockPool.stocks.map((stock) => (
                <tr key={stock.tsCode}>
                  <td>{stock.tsCode}</td>
                  <td>{stock.name}</td>
                  <td>{stock.industry}</td>
                  <td><span className={`status-chip ${stock.isPass ? "ok" : "pending"}`}>{stock.isPass ? "通过" : "阻断"}</span></td>
                  <td>{stock.filterReasons.length ? stock.filterReasons.join("、") : "--"}</td>
                  <td>{stock.listedDays}</td>
                  <td>{stock.close === null ? "--" : stock.close.toFixed(2)}</td>
                  <td>{compactMoney(stock.amount)}</td>
                  <td>{compactMoney(stock.avgAmount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function SignalSection() {
  return (
    <>
      <PageHeader title="策略信号" description={`信号日 ${signalReport.tradeDate} · 展示综合评分、买入候选、观察信号和因子解释。`} />
      <div className="stat-grid compact">
        <StatCard label="信号总数" value={`${signalReport.summary.signalCount}`} />
        <StatCard label="买入信号" value={`${signalReport.summary.buyCount}`} tone={signalReport.summary.buyCount > 0 ? "up" : "flat"} />
        <StatCard label="观察信号" value={`${signalReport.summary.watchCount}`} />
        <StatCard label="最高分" value={signalReport.signals[0] ? `${signalReport.signals[0].totalScore.toFixed(1)}` : "--"} />
      </div>
      <section className="panel">
        <h2>候选与信号</h2>
        {signalReport.signals.length === 0 ? (
          <div className="empty-state">当前交易日没有通过因子阈值的候选信号。</div>
        ) : (
          <div className="table-card">
            <table>
              <thead>
                <tr>
                  <th>代码</th>
                  <th>名称</th>
                  <th>市场</th>
                  <th>综合分</th>
                  <th>信号</th>
                  <th>目标仓位</th>
                  <th>原因</th>
                </tr>
              </thead>
              <tbody>
                {signalReport.signals.map((item) => (
                  <tr key={`${item.tsCode}-${item.signal}`}>
                    <td>{item.tsCode}</td>
                    <td>{item.name}</td>
                    <td>{item.industry}</td>
                    <td>{item.totalScore.toFixed(1)}</td>
                    <td><span className={`signal-tag ${item.signal}`}>{item.signal === "buy" ? "买入" : "观察"}</span></td>
                    <td>{item.targetWeight > 0 ? ratioPct(item.targetWeight) : "--"}</td>
                    <td>{item.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <section className="panel">
        <h2>因子评分明细</h2>
        {signalReport.signals.length === 0 ? (
          <div className="empty-state">暂无可展示的因子评分。</div>
        ) : (
          signalReport.signals.map((item) => (
            <div className="score-card" key={item.tsCode}>
              <div className="score-card-title">{item.name} · {item.totalScore.toFixed(1)} 分</div>
              <ScoreBar label="趋势结构" value={item.trendScore} />
              <ScoreBar label="相对强弱" value={item.strengthScore} />
              <ScoreBar label="量价健康" value={item.volumeScore} />
              <ScoreBar label="风险惩罚" value={item.riskScore} />
            </div>
          ))
        )}
      </section>
    </>
  );
}

function PortfolioSection() {
  return (
    <>
      <PageHeader title="持仓组合" description={`交易日 ${simulationAccount.account.lastTradeDate} · 展示模拟账户当前持仓、行业暴露、止损位置和组合状态。`} />
      <AccountStatGrid summary={simulationAccountSummary} sourceHint={`${simulationAccount.account.accountName} · ${simulationAccount.account.mode}`} />
      <section className="panel">
        <h2>持仓明细</h2>
        <PortfolioPositionTable />
      </section>
      <section className="panel">
        <h2>行业暴露</h2>
        <div className="exposure-grid">
          {simulationIndustryExposure.map((item) => (
            <div className="exposure-row" key={item.industry}>
              <span>{item.industry}</span>
              <div className="score-track"><div className="score-fill" style={{ width: `${item.weight * 100}%` }} /></div>
              <strong>{ratioPct(item.weight)}</strong>
              <em>{item.count} 只</em>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

function RiskSection() {
  return (
    <>
      <PageHeader title="风控中心" description={`交易日 ${marketRisk.tradeDate} · 集中展示市场风险、仓位限制和当前风控动作。`} />
      <div className="stat-grid compact">
        <StatCard label="风控状态" value={marketRisk.risk.state} hint={marketRisk.market.state} />
        <StatCard label="当前回撤" value={ratioPct(marketRisk.risk.currentDrawdown)} hint={`硬线 ${ratioPct(marketRisk.risk.maxDrawdownLimit)}`} tone="down" />
        <StatCard label="市场评分" value={`${marketRisk.market.score}/5`} hint="仓位映射依据" />
        <StatCard label="允许仓位" value={ratioPct(marketRisk.risk.allowedPositionWeight)} hint="市场与风控取小值" />
      </div>
      <section className="panel">
        <h2>风控动作</h2>
        <div className="action-list">
          {marketRisk.risk.actions.map((action) => <span key={action}>{action}</span>)}
        </div>
      </section>
    </>
  );
}

function BacktestSection() {
  const latestPoint = backtestResult.equityCurve.at(-1);

  return (
    <>
      <PageHeader title="回测中心" description={`策略 ${backtestResult.strategy.name} · 生成时间 ${backtestResult.generatedAt}`} />
      <div className="stat-grid compact">
        {backtestResult.cards.map((card) => (
          <StatCard key={card.label} label={card.label} value={card.value} tone={toneClass(card.tone)} />
        ))}
      </div>
      <section className="panel">
        <h2>净值曲线 / 回撤曲线</h2>
        <BacktestCurveChart />
      </section>
      <div className="two-column">
        <section className="panel">
          <h2>回测摘要</h2>
          <div className="summary-line">
            <span>期末资产</span>
            <strong>{currencyFormatter.format(backtestResult.metrics.finalAsset)}</strong>
          </div>
          <div className="summary-line">
            <span>最新净值日期</span>
            <strong>{latestPoint?.date ?? "--"}</strong>
          </div>
          <div className="summary-line">
            <span>净值点数</span>
            <strong>{backtestResult.equityCurve.length} 个交易日</strong>
          </div>
          <div className="summary-line">
            <span>总交易费用</span>
            <strong>{money(backtestResult.metrics.totalFee)} 元</strong>
          </div>
        </section>
        <section className="panel">
          <h2>参数版本</h2>
          <BacktestParameterGrid />
        </section>
      </div>
      <section className="panel">
        <h2>稳定性验证</h2>
        <div className="stat-grid compact">
          <StatCard label="验证区间" value={`${stabilityReport.period.tradingDays} 日`} hint={`${stabilityReport.period.start} - ${stabilityReport.period.end}`} />
          <StatCard label="月度胜率" value={ratioPct(stabilityReport.summary.monthlyWinRate)} hint={`${stabilityReport.summary.winningMonthCount} 胜 / ${stabilityReport.summary.losingMonthCount} 负`} />
          <StatCard label="最佳月份" value={signedRatioPct(stabilityReport.summary.bestMonthReturn)} tone={trendClass(stabilityReport.summary.bestMonthReturn)} />
          <StatCard label="最差月份" value={signedRatioPct(stabilityReport.summary.worstMonthReturn)} tone={trendClass(stabilityReport.summary.worstMonthReturn)} />
        </div>
        <div className="check-grid">
          {stabilityReport.checks.map((check) => (
            <div className="check-item" key={check.name}>
              <span className={check.passed ? "check-dot pass" : "check-dot fail"} />
              <span>{check.name}</span>
              <strong>{check.passed ? "通过" : "未过"}</strong>
            </div>
          ))}
        </div>
      </section>
      <section className="panel">
        <h2>月度收益</h2>
        <StabilityPeriodTable rows={stabilityReport.monthlyReturns} />
      </section>
      <section className="panel">
        <h2>订单明细</h2>
        <BacktestOrderTable />
      </section>
      <section className="panel">
        <h2>成交与费用</h2>
        <BacktestFillTable />
      </section>
    </>
  );
}

function ReplaySection() {
  const latestRun = replayRunLog.runs[0];

  return (
    <>
      <PageHeader title="回放验证" description={`账户 ${replaySimulationAccount.account.accountId} · ${replaySimulationAccount.equityCurve[0]?.tradeDate ?? "--"} 至 ${replaySimulationAccount.account.lastTradeDate ?? "--"}`} />
      <AccountStatGrid summary={replayAccountSummary} sourceHint={`${replaySimulationAccount.account.accountName} · ${replaySimulationAccount.account.status}`} />
      <div className="stat-grid compact">
        <StatCard label="回放交易日" value={`${replaySimulationAccount.summary.equityPointCount}`} hint={`最新 ${replaySimulationAccount.account.lastTradeDate ?? "--"}`} />
        <StatCard label="最新日收益" value={latestReplayEquity ? signedRatioPct(latestReplayEquity.dailyReturn) : "--"} tone={latestReplayEquity ? trendClass(latestReplayEquity.dailyReturn) : "flat"} />
        <StatCard label="回放风控" value={replaySimulationReport.risk.state} hint={`允许仓位 ${ratioPct(replaySimulationReport.risk.allowedPositionWeight)}`} />
        <StatCard label="运行状态" value={latestRun?.status ?? "--"} hint={latestRun ? duration(latestRun.durationMs) : "--"} tone={latestRun?.status === "success" ? "up" : "flat"} />
      </div>
      <section className="panel">
        <h2>回放权益曲线</h2>
        <AccountCurveChart accountReport={replaySimulationAccount} />
      </section>
      <div className="two-column">
        <section className="panel">
          <h2>最终市场风控</h2>
          <div className="summary-line">
            <span>交易日</span>
            <strong>{replayMarketRisk.tradeDate}</strong>
          </div>
          <div className="summary-line">
            <span>市场评分</span>
            <strong>{replayMarketRisk.market.score}/5 · {replayMarketRisk.market.state}</strong>
          </div>
          <div className="summary-line">
            <span>上涨股票占比</span>
            <strong>{replayMarketRisk.market.breadthUpPct}%</strong>
          </div>
          <div className="summary-line">
            <span>新高/新低</span>
            <strong>{replayMarketRisk.market.newHighCount} / {replayMarketRisk.market.newLowCount}</strong>
          </div>
        </section>
        <section className="panel">
          <h2>回放运行记录</h2>
          <div className="summary-line">
            <span>流程</span>
            <strong>{latestRun?.workflow ?? "--"}</strong>
          </div>
          <div className="summary-line">
            <span>股票池/信号</span>
            <strong>{latestRun ? `${latestRun.stockCount} / ${latestRun.signalCount}` : "--"}</strong>
          </div>
          <div className="summary-line">
            <span>计划/阻断</span>
            <strong>{latestRun ? `${latestRun.plannedOrderCount} / ${latestRun.blockedOrderCount}` : "--"}</strong>
          </div>
          <div className="summary-line">
            <span>错误</span>
            <strong>{latestRun?.errorMessage || "--"}</strong>
          </div>
        </section>
      </div>
      <section className="panel">
        <h2>回放持仓</h2>
        <PortfolioPositionTable accountReport={replaySimulationAccount} />
      </section>
      <section className="panel">
        <h2>回放行业暴露</h2>
        <div className="exposure-grid">
          {replayIndustryExposure.map((item) => (
            <div className="exposure-row" key={item.industry}>
              <span>{item.industry}</span>
              <div className="score-track"><div className="score-fill" style={{ width: `${item.weight * 100}%` }} /></div>
              <strong>{ratioPct(item.weight)}</strong>
              <em>{item.count} 只</em>
            </div>
          ))}
        </div>
      </section>
      <section className="panel">
        <h2>最终日订单计划</h2>
        <SimulationPlanTable report={replaySimulationReport} />
      </section>
      <section className="panel">
        <h2>回放账户订单</h2>
        <SimulationAccountOrderTable accountReport={replaySimulationAccount} />
      </section>
      <section className="panel">
        <h2>回放成交流水</h2>
        <SimulationFillTable accountReport={replaySimulationAccount} />
      </section>
    </>
  );
}

function SimulationSection() {
  return (
    <>
      <PageHeader title="模拟交易" description={`交易日 ${simulationReport.tradeDate} · 展示交易计划、真实模拟账户订单和成交约束。`} />
      <AccountStatGrid summary={simulationAccountSummary} sourceHint={`${simulationAccount.account.accountId} · ${simulationAccount.account.status}`} />
      <div className="stat-grid compact">
        <StatCard label="风控状态" value={simulationReport.risk.state} hint={`允许仓位 ${ratioPct(simulationReport.risk.allowedPositionWeight)}`} />
        <StatCard label="计划委托" value={`${simulationReport.summary.plannedOrderCount}`} hint={`${simulationReport.summary.signalCount} 个信号`} />
        <StatCard label="账户订单" value={`${simulationAccount.summary.orderCount}`} hint={`${simulationAccount.summary.fillCount} 笔成交`} />
        <StatCard label="阻断委托" value={`${simulationReport.summary.blockedOrderCount}`} hint={`${simulationReport.summary.watchCount} 个观察`} tone={simulationReport.summary.blockedOrderCount > 0 ? "down" : "flat"} />
      </div>
      <section className="panel">
        <h2>今日订单计划</h2>
        <SimulationPlanTable report={simulationReport} />
      </section>
      <section className="panel">
        <h2>模拟账户订单</h2>
        <SimulationAccountOrderTable />
      </section>
      <section className="panel">
        <h2>模拟成交流水</h2>
        <SimulationFillTable />
      </section>
      <section className="panel muted-panel">
        <h2>成交约束</h2>
        <div className="action-list">
          {simulationReport.risk.actions.map((action) => <span key={action}>{action}</span>)}
          {simulationReport.checks.map((check) => <span key={check}>{check}</span>)}
        </div>
      </section>
    </>
  );
}

function NewsSection() {
  return (
    <>
      <PageHeader title="政策新闻" description="规则词典 MVP：展示政策新闻、事件重要性、影响板块和候选个股数量。" />
      <div className="stat-grid compact">
        <StatCard label="事件数量" value={`${newsReport.summary.eventCount}`} />
        <StatCard label="利好事件" value={`${newsReport.summary.positiveCount}`} tone="up" />
        <StatCard label="利空事件" value={`${newsReport.summary.negativeCount}`} tone={newsReport.summary.negativeCount > 0 ? "down" : "flat"} />
        <StatCard label="重大事件" value={`${newsReport.summary.highImportanceCount}`} />
      </div>
      <section className="panel">
        <h2>新闻滚动</h2>
        <div className="news-list">
          {newsReport.events.map((item) => (
            <div className="news-item" key={item.title}>
              <span>{item.time}</span>
              <strong>{item.title}</strong>
              <em>{item.source}</em>
              <span className={`signal-tag ${item.sentiment === "positive" ? "buy" : "sell"}`}>{item.sentiment === "positive" ? "利好" : item.sentiment === "negative" ? "利空" : "中性"}</span>
              <span>{item.sector}</span>
              <span>重要性 {item.importance}</span>
              <span>通过 {item.passCount} 只</span>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

function DataSection() {
  const coverageTone = dataCoverage.coverageRate >= 0.98 ? "up" : dataCoverage.coverageRate >= 0.9 ? "flat" : "down";

  return (
    <>
      <PageHeader title="数据中心" description={`数据库 ${dataStatus.database} · 生成时间 ${dataStatus.generatedAt}`} />
      <div className="stat-grid compact">
        <StatCard label="最新行情日期" value={dataStatus.summary.latestTradeDate} hint="daily_bar" />
        <StatCard label="交易日历覆盖" value={dataStatus.summary.latestCalendarDate} hint="trade_calendar" />
        <StatCard label="总记录数" value={dataStatus.summary.totalRecords.toLocaleString("zh-CN")} hint={`${dataStatus.summary.tableCount} 张数据表`} />
        <StatCard label="质量异常" value={`${dataStatus.summary.qualityIssueCount}`} hint="日线 OHLC/重复校验" tone={dataStatus.summary.qualityIssueCount > 0 ? "down" : "flat"} />
      </div>
      <div className="stat-grid compact">
        <StatCard label="行情覆盖率" value={ratioPct(dataCoverage.coverageRate)} hint={`${dataCoverage.actualBarCount}/${dataCoverage.expectedBarCount} 条`} tone={coverageTone} />
        <StatCard label="覆盖股票数" value={`${dataCoverage.barStockCount}`} hint={`基础信息 ${dataCoverage.stockCount} 只`} />
        <StatCard label="覆盖交易日" value={`${dataCoverage.barTradeDayCount}`} hint={`${dataCoverage.startDate} - ${dataCoverage.endDate}`} />
        <StatCard label="缺失行情" value={`${dataCoverage.missingBarCount}`} hint="按股票 x 交易日估算" tone={dataCoverage.missingBarCount > 0 ? "down" : "flat"} />
      </div>
      <div className="two-column">
        <section className="panel">
          <h2>缺失日期</h2>
          {dataCoverage.missingByDate.length === 0 ? (
            <div className="empty-state">当前覆盖区间没有发现缺失行情。</div>
          ) : (
            <div className="table-card">
              <table className="compact-table">
                <thead>
                  <tr><th>交易日</th><th>缺失数</th><th>示例代码</th></tr>
                </thead>
                <tbody>
                  {dataCoverage.missingByDate.slice(0, 8).map((item) => (
                    <tr key={item.tradeDate}>
                      <td>{item.tradeDate}</td>
                      <td>{item.missingCount}</td>
                      <td>{item.missingCodes.join("、") || "--"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
        <section className="panel">
          <h2>缺失股票</h2>
          {dataCoverage.missingByStock.length === 0 ? (
            <div className="empty-state">当前覆盖区间没有股票级缺失。</div>
          ) : (
            <div className="table-card">
              <table className="compact-table">
                <thead>
                  <tr><th>代码</th><th>缺失交易日</th></tr>
                </thead>
                <tbody>
                  {dataCoverage.missingByStock.slice(0, 8).map((item) => (
                    <tr key={item.tsCode}>
                      <td>{item.tsCode}</td>
                      <td>{item.missingCount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
      <section className="panel">
        <h2>数据表状态</h2>
        <div className="table-card">
          <table>
            <thead>
              <tr><th>数据表</th><th>来源</th><th>状态</th><th>最新日期</th><th>记录数</th></tr>
            </thead>
            <tbody>
              {dataStatus.tables.map((task) => (
                <tr key={task.table}>
                  <td>{task.name}</td>
                  <td>{task.source}</td>
                  <td><span className={`status-chip ${task.status === "正常" ? "ok" : "pending"}`}>{task.status}</span></td>
                  <td>{task.latestDate}</td>
                  <td>{task.recordCount.toLocaleString("zh-CN")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="panel">
        <h2>质量检查</h2>
        {dataStatus.qualityIssues.length === 0 ? (
          <div className="empty-state">当前未发现日线行情质量异常。</div>
        ) : (
          <div className="table-card">
            <table>
              <thead>
                <tr><th>表</th><th>键</th><th>问题</th></tr>
              </thead>
              <tbody>
                {dataStatus.qualityIssues.map((issue) => (
                  <tr key={`${issue.table}-${issue.key}-${issue.message}`}>
                    <td>{issue.table}</td>
                    <td>{issue.key}</td>
                    <td>{issue.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

function ConfigSection() {
  const groups = [
    ["资金配置", "初始资金 500000，最大回撤硬线 15%"],
    ["持仓配置", "最多 5 只，单股上限 20%，同业最多 2 只"],
    ["买入配置", "综合分 >= 75，开盘涨幅 <= 4%，ATR <= 7%"],
    ["卖出配置", "7% 固定止损，2 * ATR20，盈利 15% 后移动止盈"],
    ["费用配置", "佣金 0.025%，印花税 0.05%，买卖滑点 0.20%"],
  ];

  return (
    <>
      <PageHeader title="策略配置" description="展示可配置参数分组，第一版只读。" />
      <div className="config-grid">
        {groups.map(([title, content]) => (
          <section className="panel" key={title}>
            <h2>{title}</h2>
            <p>{content}</p>
          </section>
        ))}
      </div>
    </>
  );
}

function ReportSection() {
  return (
    <>
      <PageHeader title="报告日志" description="沉淀每日运行结果、回测报告、风控报告和数据日志。" />
      <div className="stat-grid compact">
        <StatCard label="运行次数" value={`${runLog.summary.runCount}`} />
        <StatCard label="成功" value={`${runLog.summary.successCount}`} tone={runLog.summary.successCount > 0 ? "up" : "flat"} />
        <StatCard label="失败" value={`${runLog.summary.failedCount}`} tone={runLog.summary.failedCount > 0 ? "down" : "flat"} />
        <StatCard label="最新状态" value={runLog.summary.latestStatus} hint={runLog.summary.latestTradeDate} />
      </div>
      <section className="panel">
        <h2>最近运行</h2>
        {runLog.runs.length === 0 ? (
          <div className="empty-state">暂无模拟盘运行日志。运行 paper-pipeline 后会在这里显示任务状态。</div>
        ) : (
          <div className="table-card">
            <table className="backtest-table">
              <thead>
                <tr>
                  <th>开始时间</th>
                  <th>流程</th>
                  <th>数据源</th>
                  <th>账户</th>
                  <th>交易日</th>
                  <th>状态</th>
                  <th>耗时</th>
                  <th>股票池</th>
                  <th>信号</th>
                  <th>计划/阻断</th>
                  <th>订单/成交</th>
                  <th>错误</th>
                </tr>
              </thead>
              <tbody>
                {runLog.runs.map((run) => (
                  <tr key={run.runId}>
                    <td>{run.startedAt}</td>
                    <td>{run.workflow}</td>
                    <td>{run.source}</td>
                    <td>{run.accountId ?? "--"}</td>
                    <td>{run.tradeDate ?? "--"}</td>
                    <td><span className={`status-chip ${run.status === "success" ? "ok" : "pending"}`}>{run.status}</span></td>
                    <td>{duration(run.durationMs)}</td>
                    <td>{run.stockCount}</td>
                    <td>{run.signalCount}</td>
                    <td>{run.plannedOrderCount} / {run.blockedOrderCount}</td>
                    <td>{run.orderCount} / {run.fillCount}</td>
                    <td>{run.errorMessage || "--"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

export function DashboardSections({ activeItem }: DashboardSectionsProps) {
  switch (activeItem) {
    case "首页总览":
      return <HomeSection />;
    case "市场环境":
      return <MarketSection />;
    case "股票池":
      return <UniverseSection />;
    case "策略信号":
      return <SignalSection />;
    case "持仓组合":
      return <PortfolioSection />;
    case "风控中心":
      return <RiskSection />;
    case "回测中心":
      return <BacktestSection />;
    case "回放验证":
      return <ReplaySection />;
    case "模拟交易":
      return <SimulationSection />;
    case "政策新闻":
      return <NewsSection />;
    case "数据中心":
      return <DataSection />;
    case "策略配置":
      return <ConfigSection />;
    case "报告日志":
      return <ReportSection />;
    default:
      return <HomeSection />;
  }
}
