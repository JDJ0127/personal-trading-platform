import rawIndexQuotes from "../data/indexQuotes.json";
import { accountSummary, type IndexQuote } from "../data/mockData";

const indexQuotes = rawIndexQuotes.quotes as IndexQuote[];

export function TopBar() {
  return (
    <header className="top-bar">
      <div className="brand-block">
        <div className="brand-title">
          个人交易平台
          <span className="brand-subtitle">{accountSummary.mode}</span>
        </div>
      </div>

      <div className="index-strip" aria-label="主要指数实时数据">
        {indexQuotes.map((quote) => (
          <div className="index-card" key={quote.code}>
            <div className="index-name">{quote.name}</div>
            <div className="index-value">{quote.value.toFixed(2)}</div>
            <div className={`market-change ${quote.trend}`}>
              {quote.change > 0 ? "+" : ""}
              {quote.change.toFixed(2)} / {quote.changePct > 0 ? "+" : ""}
              {quote.changePct.toFixed(2)}%
            </div>
          </div>
        ))}
      </div>

      <div className="account-clock">
        <div className="account-name">{accountSummary.accountName}</div>
      </div>
    </header>
  );
}
