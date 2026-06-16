export type Trend = "up" | "down" | "flat";

export type IndexQuote = {
  name: string;
  code: string;
  value: number;
  change: number;
  changePct: number;
  updatedAt: string;
  trend: Trend;
};

export type AccountSummary = {
  accountName: string;
  mode: string;
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

export type Holding = {
  code: string;
  name: string;
  industry: string;
  quantity: number;
  costPrice: number;
  marketPrice: number;
  weight: number;
  pnlPct: number;
  holdingDays: number;
  stopPrice: number;
  atrVolatility: number;
};

export type Candidate = {
  code: string;
  name: string;
  industry: string;
  totalScore: number;
  trendScore: number;
  strengthScore: number;
  volumeScore: number;
  industryScore: number;
  riskScore: number;
  signal: "buy" | "sell" | "hold" | "watch";
  targetWeight: number;
  reason: string;
};

export type RiskState = {
  state: "Normal" | "Caution" | "Defensive" | "PauseBuy" | "DeRisk" | "Stop";
  currentDrawdown: number;
  maxDrawdownLimit: number;
  dailyLoss: number;
  weeklyLoss: number;
  maxPositionWeight: number;
  allowedPositionWeight: number;
  actions: string[];
};

export const navItems = [
  "首页总览",
  "市场环境",
  "股票池",
  "策略信号",
  "持仓组合",
  "风控中心",
  "回测中心",
  "回放验证",
  "模拟交易",
  "政策新闻",
  "数据中心",
  "策略配置",
  "报告日志",
] as const;

export type NavItem = (typeof navItems)[number];

export const indexQuotes: IndexQuote[] = [
  { name: "上证", code: "000001.SH", value: 3047.86, change: 18.24, changePct: 0.6, updatedAt: "14:55:03", trend: "up" },
  { name: "深证", code: "399001.SZ", value: 9841.35, change: -22.18, changePct: -0.22, updatedAt: "14:55:03", trend: "down" },
  { name: "创业板", code: "399006.SZ", value: 1968.44, change: 11.62, changePct: 0.59, updatedAt: "14:55:03", trend: "up" },
  { name: "科创板", code: "000688.SH", value: 812.71, change: 0.86, changePct: 0.11, updatedAt: "14:55:03", trend: "up" },
];

export const accountSummary: AccountSummary = {
  accountName: "个人模拟账户",
  mode: "模拟盘",
  totalAsset: 518420,
  cash: 213680,
  marketValue: 304740,
  dailyReturn: 0.72,
  cumulativeReturn: 3.68,
  currentDrawdown: 4.2,
  maxDrawdown: 7.8,
  totalWeight: 58.8,
  positionCount: 4,
};

export const marketRegime = {
  score: 3,
  state: "震荡偏强",
  maxWeight: 60,
  breadthUpPct: 56.8,
  newHigh20d: 312,
  newLow20d: 188,
  checks: [
    { name: "沪深 300 > 60 日均线", passed: true },
    { name: "中证 500 > 60 日均线", passed: true },
    { name: "中证 1000 > 60 日均线", passed: false },
    { name: "上涨股票占比 > 55%", passed: true },
    { name: "20 日新高数 > 新低数", passed: false },
  ],
};

export const holdings: Holding[] = [
  { code: "300750", name: "宁德时代", industry: "电力设备", quantity: 300, costPrice: 184.2, marketPrice: 191.8, weight: 11.1, pnlPct: 4.13, holdingDays: 6, stopPrice: 174.6, atrVolatility: 3.8 },
  { code: "688981", name: "中芯国际", industry: "电子", quantity: 1200, costPrice: 47.6, marketPrice: 49.3, weight: 11.4, pnlPct: 3.57, holdingDays: 4, stopPrice: 44.8, atrVolatility: 4.6 },
  { code: "600030", name: "中信证券", industry: "非银金融", quantity: 2600, costPrice: 21.25, marketPrice: 20.82, weight: 10.4, pnlPct: -2.02, holdingDays: 8, stopPrice: 19.76, atrVolatility: 2.9 },
  { code: "002475", name: "立讯精密", industry: "电子", quantity: 1800, costPrice: 34.3, marketPrice: 36.2, weight: 12.6, pnlPct: 5.54, holdingDays: 5, stopPrice: 32.1, atrVolatility: 4.2 },
];

export const candidates: Candidate[] = [
  { code: "300308", name: "中际旭创", industry: "通信", totalScore: 86, trendScore: 88, strengthScore: 91, volumeScore: 83, industryScore: 84, riskScore: 78, signal: "buy", targetWeight: 12, reason: "行业强度提升，趋势结构完整，开盘确认后可建仓" },
  { code: "601138", name: "工业富联", industry: "电子", totalScore: 82, trendScore: 80, strengthScore: 86, volumeScore: 79, industryScore: 81, riskScore: 76, signal: "watch", targetWeight: 0, reason: "综合分达标，但上方压力区较近，先观察" },
  { code: "600036", name: "招商银行", industry: "银行", totalScore: 78, trendScore: 75, strengthScore: 72, volumeScore: 76, industryScore: 68, riskScore: 88, signal: "hold", targetWeight: 10, reason: "低波动持有标的，未触发加仓" },
  { code: "600030", name: "中信证券", industry: "非银金融", totalScore: 64, trendScore: 59, strengthScore: 61, volumeScore: 58, industryScore: 70, riskScore: 66, signal: "sell", targetWeight: 0, reason: "跌破 20 日均线且综合分下滑" },
];

export const riskState: RiskState = {
  state: "Caution",
  currentDrawdown: 4.2,
  maxDrawdownLimit: 15,
  dailyLoss: 0,
  weeklyLoss: 1.1,
  maxPositionWeight: 60,
  allowedPositionWeight: 60,
  actions: ["每日最多新增 1 只", "优先选择低 ATR 候选", "保持行业暴露低于 40%"],
};

export const industryExposure = [
  { industry: "电子", weight: 24.0, count: 2 },
  { industry: "电力设备", weight: 11.1, count: 1 },
  { industry: "非银金融", weight: 10.4, count: 1 },
  { industry: "现金", weight: 41.2, count: 0 },
];

export const dataTasks = [
  { name: "日线行情", source: "Tushare", status: "正常", latestDate: "2026-06-11" },
  { name: "指数行情", source: "Tushare", status: "正常", latestDate: "2026-06-11" },
  { name: "实时快照", source: "AkShare", status: "模拟", latestDate: "2026-06-12" },
  { name: "新闻快讯", source: "AkShare", status: "待接入", latestDate: "--" },
];

export const newsItems = [
  { time: "09:18", source: "交易所公告", title: "半导体设备产业链订单增速改善", sentiment: "positive", importance: 72, sector: "半导体设备", passCount: 2 },
  { time: "10:42", source: "财经快讯", title: "部分高位题材股出现资金分歧", sentiment: "negative", importance: 63, sector: "高位主题", passCount: 0 },
  { time: "13:20", source: "公开政策源", title: "新型基础设施建设支持政策延续", sentiment: "positive", importance: 81, sector: "算力、数据中心", passCount: 3 },
];

export const reports = [
  { date: "2026-06-11", type: "日报", title: "市场评分 3 分，观察池新增 2 只" },
  { date: "2026-06-10", type: "风控", title: "账户回撤进入 Caution 阈值附近" },
  { date: "2026-06-09", type: "回测", title: "MVP 趋势策略样例报告生成" },
];
