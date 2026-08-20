"use client";

import { useState, useEffect, useRef } from "react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { Search, TrendingUp, Activity, BarChart2, Cpu, X, Info, AlertCircle, TrendingDown, Trophy, AlertTriangle } from "lucide-react";

const METRIC_DICT: Record<string, { desc: string; formulaTop: string; formulaBot: string }> = {
  PE_Ratio: { desc: "Price-to-Earnings ratio measures a company's current share price relative to its per-share earnings.", formulaTop: "Market Price per Share", formulaBot: "Earnings per Share (EPS)" },
  Forward_PE: { desc: "Forward P/E uses forecasted earnings to evaluate future valuation rather than trailing historical data.", formulaTop: "Market Price per Share", formulaBot: "Estimated Future EPS" },
  PEG_Ratio: { desc: "The P/E ratio divided by the EPS growth rate. Helps normalize valuation for high-growth companies.", formulaTop: "P/E Ratio", formulaBot: "Earnings Growth Rate" },
  PB_Ratio: { desc: "Price-to-Book ratio compares a firm's market capitalization to its accounting book value.", formulaTop: "Market Price per Share", formulaBot: "Book Value per Share" },
  PS_Ratio: { desc: "Price-to-Sales compares a company's stock price to its total revenues.", formulaTop: "Market Capitalization", formulaBot: "Total Revenue" },
  EV_EBITDA: { desc: "Enterprise Value to EBITDA measures the total value of a company relative to its operational cash flow.", formulaTop: "Enterprise Value (EV)", formulaBot: "EBITDA" },
  EV_Sales: { desc: "Enterprise Value to Sales. Useful for valuing companies with negative earnings.", formulaTop: "Enterprise Value (EV)", formulaBot: "Total Revenue" },
  ROE: { desc: "Return on Equity represents financial performance calculated by dividing net income by shareholders' equity.", formulaTop: "Net Income", formulaBot: "Shareholders' Equity" },
  ROA: { desc: "Return on Assets shows how profitable a company is relative to its total overall assets.", formulaTop: "Net Income", formulaBot: "Total Assets" },
  Gross_Margin: { desc: "Gross Margin represents the percentage of total sales revenue that a company retains after incurring direct costs associated with producing goods.", formulaTop: "Revenue - COGS", formulaBot: "Total Revenue" },
  Operating_Margin: { desc: "Measures how much profit a company makes on a dollar of sales after paying for variable costs of production.", formulaTop: "Operating Income", formulaBot: "Total Revenue" },
  Net_Margin: { desc: "Measures how much net income is generated as a percentage of total revenue.", formulaTop: "Net Income", formulaBot: "Total Revenue" },
  Debt_to_Equity: { desc: "The Debt-to-Equity ratio calculates the proportion of total liabilities to shareholder equity.", formulaTop: "Total Liabilities", formulaBot: "Shareholders' Equity" },
  Current_Ratio: { desc: "The Current Ratio evaluates a company's ability to pay short-term obligations due within one year.", formulaTop: "Current Assets", formulaBot: "Current Liabilities" },
  Quick_Ratio: { desc: "Measures a company's capacity to pay its current liabilities without needing to sell its inventory.", formulaTop: "Current Assets - Inventory", formulaBot: "Current Liabilities" },
  Dividend_Yield: { desc: "Shows how much a company pays out in dividends each year relative to its stock price.", formulaTop: "Annual Dividends per Share", formulaBot: "Market Price per Share" },
  Payout_Ratio: { desc: "The proportion of earnings paid out as dividends to shareholders.", formulaTop: "Dividends Paid", formulaBot: "Net Income" }
};

const FALLBACK_TICKERS = [
  { symbol: "AAPL", title: "Apple Inc." },
  { symbol: "MSFT", title: "Microsoft Corporation" }
];

export default function Home() {
  const [activeTab, setActiveTab] = useState("Valuation Terminal");
  
  const [tickers, setTickers] = useState<{ symbol: string; title: string }[]>(FALLBACK_TICKERS);
  const [searchQuery, setSearchQuery] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  
  const [valuationData, setValuationData] = useState<any>(null);
  const [chartData, setChartData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState<string | null>(null);
  
  const [timeframe, setTimeframe] = useState("1M");
  const [benchmarkContext, setBenchmarkContext] = useState<"industry" | "market">("industry");
  const [selectedMetricModal, setSelectedMetricModal] = useState<string | null>(null);
  const searchRef = useRef<HTMLDivElement>(null);

  const [industries, setIndustries] = useState<string[]>(["All Industries"]);
  const [rankingIndustry, setRankingIndustry] = useState("All Industries");
  const [rankingContext, setRankingContext] = useState<"Industry" | "Market">("Industry");
  const [rankingsData, setRankingsData] = useState<{top_10: any[], bottom_10: any[]} | null>(null);
  const [rankingsLoading, setRankingsLoading] = useState(false);

  const TIMEFRAMES = ["1D", "1W", "1M", "3M", "6M", "1Y", "5Y", "ALL"];

  useEffect(() => {
    fetch("http://localhost:8000/tickers")
      .then(res => res.json())
      .then(data => { if (data.tickers) setTickers(data.tickers); })
      .catch(e => console.warn(e));

    fetch("http://localhost:8000/industries")
      .then(res => res.json())
      .then(data => { if (data.industries) setIndustries(["All Industries", ...data.industries]); })
      .catch(e => console.error(e));

    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) setShowSuggestions(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (activeTab === "Market Rankings") {
      setRankingsLoading(true);
      fetch(`http://localhost:8000/rankings?industry=${encodeURIComponent(rankingIndustry)}&context=${rankingContext}`)
        .then(res => res.json())
        .then(data => setRankingsData(data))
        .catch(e => console.error(e))
        .finally(() => setRankingsLoading(false));
    }
  }, [activeTab, rankingIndustry, rankingContext]);

  const calculateCompositeZScore = (metrics: any, benchmarks: any) => {
    if (!metrics || !benchmarks) return 0;
    let totalZ = 0, validCount = 0;
    Object.keys(benchmarks).forEach((m_name) => {
      const b_data = benchmarks[m_name]?.[benchmarkContext];
      const val = metrics[m_name];
      if (b_data && b_data.mean !== null && val !== null && val !== undefined) {
        const mean = b_data.mean;
        const std = b_data.std || 1;
        let z = (val - mean) / std;
        if (benchmarks[m_name].lower_is_better) z = -z;
        totalZ += z;
        validCount++;
      }
    });
    return validCount > 0 ? (totalZ / validCount) : 0;
  };

  const getPercentile = (z: number) => {
    const sign = z >= 0 ? 1 : -1;
    const x = Math.abs(z) / Math.sqrt(2);
    const t = 1.0 / (1.0 + 0.3275911 * x);
    const erf = sign * (1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x));
    return (0.5 * (1 + erf) * 100).toFixed(1);
  };

  const generateBellCurveData = (mean: number, std: number) => {
    if (!std) return [];
    const data = [];
    for (let x = mean - std * 4; x <= mean + std * 4; x += (std * 8) / 60) {
      const y = (1 / (std * Math.sqrt(2 * Math.PI))) * Math.exp(-0.5 * Math.pow((x - mean) / std, 2));
      data.push({ x, y });
    }
    return data;
  };

  const handleSelectTicker = (tickerSymbol: string) => {
    setSelectedTicker(tickerSymbol);
    setSearchQuery(tickerSymbol);
    setShowSuggestions(false);
    setActiveTab("Valuation Terminal");
    fetchData(tickerSymbol);
  };

  const fetchHistory = async (ticker: string, period: string) => {
    setChartLoading(true); setChartError(null);
    try {
      const res = await fetch(`http://localhost:8000/history/${ticker}?period=${period}`);
      if (res.ok) {
        const hist = await res.json();
        if (hist.history && hist.history.length > 0) setChartData(hist.history);
        else { setChartData([]); setChartError(hist.error || "No market data available."); }
      } else { setChartData([]); setChartError("Failed to connect to server."); }
    } catch { setChartData([]); setChartError("Network error."); } 
    finally { setChartLoading(false); }
  };

  const fetchData = async (ticker: string) => {
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/manual-valuation/${ticker}`);
      if (res.ok) setValuationData(await res.json());
    } catch (e) { console.error(e); } 
    finally { setLoading(false); }
    fetchHistory(ticker, timeframe);
  };

  useEffect(() => { if (selectedTicker) fetchHistory(selectedTicker, timeframe); }, [timeframe]);

  const formatValue = (name: string, val: number) => {
    if (val === null || val === undefined) return "N/A";
    const str = name.toLowerCase();
    return (str.includes("margin") || str.includes("roe") || str.includes("roa") || str.includes("yield") || str.includes("payout")) 
      ? `${(val * 100).toFixed(2)}%` : val.toFixed(2);
  };

  const formatXAxis = (tickItem: string) => {
    if (!tickItem) return "";
    return (timeframe === "1D" || timeframe === "1W") && tickItem.includes(" ") ? tickItem.split(" ")[1] : tickItem;
  };

  let chartColor = "#A8C7FA", priceChange = 0, percentChange = 0, isPositive = true;
  if (chartData.length > 0) {
    const start = chartData[0].price, end = chartData[chartData.length - 1].price;
    priceChange = end - start;
    percentChange = start > 0 ? (priceChange / start) * 100 : 0;
    isPositive = priceChange >= 0;
    chartColor = isPositive ? "#10B981" : "#EF4444"; 
  }
  const sign = isPositive ? "+" : "";
  const currentPrice = valuationData?.price || 0;

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const hoverPrice = payload[0].value;
      const diff = hoverPrice - (chartData[0]?.price || hoverPrice);
      const hoverIsPos = diff >= 0;
      return (
        <div className="bg-[#161A23] border border-white/10 p-4 rounded-xl shadow-2xl backdrop-blur-md">
          <p className="text-[#9CA3AF] text-xs font-bold mb-1 tracking-widest uppercase">{label}</p>
          <p className="text-white text-2xl font-black mb-1">${hoverPrice.toFixed(2)}</p>
          <p className="text-sm font-bold flex items-center gap-1" style={{ color: hoverIsPos ? "#10B981" : "#EF4444" }}>
            {hoverIsPos ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            {hoverIsPos ? "+" : ""}${Math.abs(diff).toFixed(2)} ({hoverIsPos ? "+" : ""}{(diff / (chartData[0]?.price || hoverPrice) * 100).toFixed(2)}%)
          </p>
        </div>
      );
    }
    return null;
  };

  const filteredTickers = tickers.filter(t => t.symbol.toLowerCase().includes(searchQuery.toLowerCase()) || t.title.toLowerCase().includes(searchQuery.toLowerCase())).slice(0, 15);
  
  const menuItems = [
    { name: "Valuation Terminal", icon: <Search size={22} /> },
    { name: "Market Rankings", icon: <BarChart2 size={22} /> },
    { name: "Options & Volatility", icon: <Activity size={22} /> },
    { name: "AI Predictive Modeling", icon: <Cpu size={22} /> },
  ];

  return (
    <div className="flex h-screen bg-[#0B0E14] text-[#E2E2E2] font-sans overflow-hidden">
      
      {/* Metric Info Modal */}
      {selectedMetricModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-[#161A23] border border-white/10 p-8 rounded-2xl shadow-2xl max-w-md w-full relative">
            <button onClick={() => setSelectedMetricModal(null)} className="absolute top-4 right-4 text-[#9CA3AF] hover:text-white transition-colors"><X size={24} /></button>
            <div className="flex items-center gap-3 mb-6">
              <Info className="text-[#A8C7FA]" size={28} />
              <h3 className="text-2xl font-extrabold text-white">{selectedMetricModal.replace(/_/g, " ")}</h3>
            </div>
            <div className="bg-[#0B0E14] border border-white/5 p-6 rounded-xl flex flex-col items-center justify-center mb-6">
              <span className="text-sm text-[#9CA3AF] font-bold tracking-widest uppercase mb-4">Calculation Formula</span>
              <div className="text-lg font-bold text-white text-center">
                <div className="px-4 pb-2 border-b-2 border-white/20">{METRIC_DICT[selectedMetricModal]?.formulaTop || "Numerator"}</div>
                <div className="px-4 pt-2">{METRIC_DICT[selectedMetricModal]?.formulaBot || "Denominator"}</div>
              </div>
            </div>
            <div>
              <span className="text-sm text-[#9CA3AF] font-bold tracking-widest uppercase block mb-2">Financial Meaning</span>
              <p className="text-[#E2E2E2] leading-relaxed">{METRIC_DICT[selectedMetricModal]?.desc || "No description available."}</p>
            </div>
          </div>
        </div>
      )}

      {/* Sidebar Navigation */}
      <aside className="w-72 bg-[#161A23] border-r border-white/5 flex flex-col z-20 shadow-2xl">
        <div className="p-8 mb-2">
          <h1 className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-white to-[#A8C7FA] tracking-tight">Quant Engine</h1>
        </div>
        <nav className="flex-1 px-4 space-y-2">
          {menuItems.map((item) => (
            <button key={item.name} onClick={() => setActiveTab(item.name)} className={`w-full flex items-center gap-4 px-5 py-4 rounded-xl text-left transition-all duration-300 ${activeTab === item.name ? "bg-[#A8C7FA]/10 border-l-4 border-[#A8C7FA] text-white shadow-lg" : "border-l-4 border-transparent text-[#9CA3AF] hover:bg-white/5 hover:text-white"}`}>
              <span className={activeTab === item.name ? "text-[#A8C7FA]" : ""}>{item.icon}</span>
              <span className="font-semibold text-[1.05rem] tracking-wide">{item.name}</span>
            </button>
          ))}
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto relative p-10 scroll-smooth">
        <div className="absolute top-0 left-0 w-full h-96 bg-[#A8C7FA]/5 blur-[120px] -z-10"></div>
        <header className="mb-8 flex justify-between items-end">
          <h2 className="text-4xl font-extrabold tracking-tight text-white">{activeTab}</h2>
        </header>

        {/* ------------------------------------------------------------------------------------------------- */}
        {/* MODULE 1: VALUATION TERMINAL */}
        {/* ------------------------------------------------------------------------------------------------- */}
        {activeTab === "Valuation Terminal" && (
          <div className="space-y-8 animate-in fade-in duration-500">
            <div className="relative z-40" ref={searchRef}>
              <div className="glass-panel flex items-center px-6 py-4 focus-within:border-[#A8C7FA]/50 transition-all shadow-lg">
                <Search className="text-[#9CA3AF] mr-4" size={24} />
                <input type="text" placeholder="Search 900+ companies by ticker or name..." className="w-full bg-transparent border-none outline-none text-white text-lg font-medium placeholder-[#9CA3AF]/50" value={searchQuery} onChange={(e) => { setSearchQuery(e.target.value); setShowSuggestions(true); }} onFocus={() => setShowSuggestions(true)} />
                {searchQuery && <button onClick={() => { setSearchQuery(""); setShowSuggestions(false); }} className="text-[#9CA3AF] hover:text-white ml-2"><X size={20} /></button>}
              </div>
              {showSuggestions && searchQuery && filteredTickers.length > 0 && (
                <ul className="absolute top-full left-0 w-full bg-[#1D222E] border border-white/10 mt-2 rounded-xl shadow-2xl max-h-72 overflow-y-auto animate-in slide-in-from-top-2">
                  {filteredTickers.map((t) => (
                    <li key={t.symbol} onClick={() => handleSelectTicker(t.symbol)} className="px-6 py-4 hover:bg-[#A8C7FA]/10 cursor-pointer flex justify-between items-center transition-colors border-b border-white/5 last:border-none">
                      <span className="font-bold text-white">{t.title}</span><span className="text-sm font-black px-2 py-1 bg-white/5 rounded text-[#A8C7FA] tracking-widest">{t.symbol}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {loading && <div className="flex flex-col items-center justify-center py-20 animate-pulse"><Activity size={48} className="text-[#A8C7FA] mb-4" /><p className="text-[#9CA3AF] font-medium tracking-wide">Synthesizing Core Data...</p></div>}

            {!loading && valuationData && (
              <div className="space-y-6 animate-in slide-in-from-bottom-4 duration-700">
                <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                  {/* Dynamic Price Chart Panel */}
                  <div className="xl:col-span-2 glass-panel p-8 relative">
                    <div className="flex flex-col xl:flex-row justify-between items-start mb-8">
                      <div className="flex flex-col items-start">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="text-xl font-black px-3 py-1 bg-white/5 border border-white/10 rounded-lg text-white tracking-widest shadow-sm">{selectedTicker}</span>
                          <h3 className="text-2xl font-bold text-white opacity-90">{valuationData.company_name}</h3>
                        </div>
                        <div className="text-5xl font-black text-white mt-1">${currentPrice.toFixed(2)}</div>
                        {!chartLoading && chartData.length > 0 && (
                          <div className={`text-lg font-bold mt-2 flex items-center gap-2 ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                            {isPositive ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
                            <span>{sign}${Math.abs(priceChange).toFixed(2)}</span><span>({sign}{percentChange.toFixed(2)}%)</span>
                            <span className="text-sm font-medium opacity-60 ml-1">Past {timeframe}</span>
                          </div>
                        )}
                      </div>
                      <div className="flex bg-[#0B0E14] p-1.5 rounded-xl border border-white/10 mt-6 xl:mt-0 shadow-inner self-start xl:self-end">
                        {TIMEFRAMES.map((tf) => (
                          <button key={tf} onClick={() => setTimeframe(tf)} className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${timeframe === tf ? "bg-white/10 text-white shadow-md" : "text-[#9CA3AF] hover:text-white"}`}>{tf}</button>
                        ))}
                      </div>
                    </div>
                    <div className="h-80 w-full mt-4">
                      {chartLoading ? ( <div className="w-full h-full flex flex-col items-center justify-center text-[#9CA3AF] animate-pulse"><Activity size={32} className="mb-2 opacity-50" />Fetching market action...</div> ) : chartError ? ( <div className="w-full h-full flex flex-col items-center justify-center text-red-400/80 bg-red-500/5 rounded-xl border border-red-500/10"><AlertCircle size={36} className="mb-2" /><span className="font-bold">{chartError}</span></div> ) : (
                        <ResponsiveContainer width="100%" height="100%">
                          <AreaChart data={chartData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                            <defs><linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={chartColor} stopOpacity={0.4}/><stop offset="95%" stopColor={chartColor} stopOpacity={0}/></linearGradient></defs>
                            <XAxis dataKey="date" tick={{ fill: '#9CA3AF', fontSize: 11 }} axisLine={false} tickLine={false} minTickGap={40} tickFormatter={formatXAxis} />
                            <YAxis domain={['dataMin', 'dataMax']} tick={{ fill: '#9CA3AF', fontSize: 11 }} tickFormatter={(v) => `$${v.toFixed(0)}`} axisLine={false} tickLine={false} orientation="right" />
                            <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.2)', strokeWidth: 1, strokeDasharray: '4 4' }} />
                            <Area type="monotone" dataKey="price" stroke={chartColor} strokeWidth={3} fillOpacity={1} fill="url(#colorPrice)" />
                          </AreaChart>
                        </ResponsiveContainer>
                      )}
                    </div>
                  </div>

                  {/* Verdict Panel */}
                  <div className="glass-panel p-8 flex flex-col justify-between relative overflow-hidden">
                    <div className={`absolute top-0 right-0 w-48 h-48 rounded-full blur-3xl pointer-events-none ${chartColor === "#10B981" ? 'bg-emerald-500/10' : 'bg-red-500/10'}`}></div>
                    <div>
                      <h4 className="text-sm font-bold text-white uppercase tracking-widest mb-2 border-b border-white/10 pb-2">Quantitative Verdict</h4>
                      {(() => {
                        const zScore = calculateCompositeZScore(valuationData.metrics, valuationData.benchmarks);
                        const zScoreColor = zScore >= 0 ? "text-emerald-400" : "text-red-400";
                        const boundedZ = Math.max(-4, Math.min(4, zScore));
                        return (
                          <div className="mt-4">
                            <p className="text-[#9CA3AF] text-sm leading-relaxed mb-6">Aggregated standard deviations relative to the <strong>{benchmarkContext}</strong> universe.</p>
                            <div className="flex items-baseline gap-3 mb-2"><div className={`text-6xl font-black ${zScoreColor}`}>{zScore > 0 ? "+" : ""}{zScore.toFixed(2)}</div></div>
                            <div className="text-xl font-bold text-white opacity-90 mb-6">Top {100 - Number(getPercentile(zScore))}% Percentile</div>
                            <div className="h-32 w-full mt-4">
                               <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={generateBellCurveData(0, 1)}>
                                  <XAxis dataKey="x" type="number" hide domain={[-4, 4]} />
                                  <YAxis hide />
                                  <Area type="monotone" dataKey="y" stroke="none" fill="#374151" fillOpacity={0.8} />
                                  <ReferenceLine x={boundedZ} stroke={zScore >= 0 ? "#10B981" : "#EF4444"} strokeWidth={4} />
                                </AreaChart>
                              </ResponsiveContainer>
                            </div>
                            <div className="flex justify-between text-[0.7rem] text-[#9CA3AF] font-bold uppercase mt-2 tracking-widest"><span>Overvalued (-Z)</span><span>Average (0)</span><span>Undervalued (+Z)</span></div>
                          </div>
                        );
                      })()}
                    </div>
                  </div>
                </div>

                <div className="flex justify-between items-end mt-10 mb-4 border-b border-white/10 pb-4">
                  <h4 className="text-2xl font-extrabold text-white">Fundamental Metrics & Distributions</h4>
                  <div className="flex bg-[#0B0E14] p-1.5 rounded-xl border border-white/10">
                    <button onClick={() => setBenchmarkContext("industry")} className={`px-5 py-2 rounded-lg text-sm font-bold transition-all ${benchmarkContext === "industry" ? "bg-white/10 text-white" : "text-[#9CA3AF] hover:text-white"}`}>Industry Peers</button>
                    <button onClick={() => setBenchmarkContext("market")} className={`px-5 py-2 rounded-lg text-sm font-bold transition-all ${benchmarkContext === "market" ? "bg-white/10 text-white" : "text-[#9CA3AF] hover:text-white"}`}>Total Market</button>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
                  {valuationData.metrics && valuationData.benchmarks && Object.entries(valuationData.metrics).map(([key, val]: [string, any]) => {
                    const bench = valuationData.benchmarks[key]?.[benchmarkContext];
                    if (!bench || bench.mean === null) return null;
                    const mean = bench.mean, std = bench.std || 1;
                    let z = (val - mean) / std;
                    const isLowerBetter = valuationData.benchmarks[key]?.lower_is_better;
                    const isGood = isLowerBetter ? z < 0 : z > 0;
                    const markerColor = isGood ? "#10B981" : "#EF4444";
                    const boundedZ = Math.max(-4, Math.min(4, z));
                    return (
                      <div key={key} onClick={() => setSelectedMetricModal(key)} className="bg-[#161A23] p-6 rounded-2xl border border-white/5 shadow-lg hover:border-[#A8C7FA]/40 hover:-translate-y-1 transition-all cursor-pointer group relative overflow-hidden flex flex-col justify-between">
                        <div className="flex justify-between items-start mb-4"><div className="text-sm font-bold text-[#9CA3AF] group-hover:text-white transition-colors uppercase tracking-wider">{key.replace(/_/g, " ")}</div><div className="text-xs px-2 py-1 bg-white/5 rounded text-[#9CA3AF] opacity-0 group-hover:opacity-100 transition-opacity">Formula ↗</div></div>
                        <div className="flex justify-between items-start mb-6">
                          <div><div className="text-3xl font-black text-white">{formatValue(key, val)}</div><div className="text-xs text-[#9CA3AF] font-bold mt-1">Mean: <span className="text-[#E2E2E2]">{formatValue(key, mean)}</span></div></div>
                          <div className="text-right"><div className={`text-lg font-bold ${isGood ? "text-emerald-400" : "text-red-400"}`}>Z: {isLowerBetter ? -z.toFixed(2) : z.toFixed(2)}</div></div>
                        </div>
                        <div className="h-16 w-full opacity-80 group-hover:opacity-100 transition-opacity">
                           <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={generateBellCurveData(mean, std)}><XAxis dataKey="x" type="number" hide domain={['dataMin', 'dataMax']} /><YAxis hide /><Area type="monotone" dataKey="y" stroke="none" fill="#374151" fillOpacity={0.6} /><ReferenceLine x={mean + (boundedZ * std)} stroke={markerColor} strokeWidth={3} /></AreaChart>
                          </ResponsiveContainer>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ------------------------------------------------------------------------------------------------- */}
        {/* MODULE 2: MARKET RANKINGS */}
        {/* ------------------------------------------------------------------------------------------------- */}
        {activeTab === "Market Rankings" && (
          <div className="space-y-8 animate-in fade-in duration-500">
            
            {/* Header Controls */}
            <div className="glass-panel p-6 flex flex-col lg:flex-row justify-between items-center gap-6 relative z-20">
              <div className="w-full lg:w-1/3">
                <label className="block text-xs font-bold text-[#A8C7FA] mb-2 uppercase tracking-widest">Select Universe Filter</label>
                <select 
                  className="w-full bg-[#0B0E14] border border-white/10 rounded-xl px-4 py-3.5 text-white font-medium outline-none cursor-pointer" 
                  value={rankingIndustry} 
                  onChange={(e) => setRankingIndustry(e.target.value)}
                >
                  {industries.map(ind => <option key={ind} value={ind}>{ind}</option>)}
                </select>
              </div>
              <div className="w-full lg:w-auto flex justify-end">
                <div className="flex bg-[#0B0E14] p-1.5 rounded-xl border border-white/10 shadow-inner">
                  <button onClick={() => setRankingContext("Industry")} className={`px-6 py-2.5 rounded-lg text-sm font-bold transition-all ${rankingContext === "Industry" ? "bg-white/10 text-white shadow-md" : "text-[#9CA3AF] hover:text-white"}`}>Industry Z-Score</button>
                  <button onClick={() => setRankingContext("Market")} className={`px-6 py-2.5 rounded-lg text-sm font-bold transition-all ${rankingContext === "Market" ? "bg-white/10 text-white shadow-md" : "text-[#9CA3AF] hover:text-white"}`}>Market Z-Score</button>
                </div>
              </div>
            </div>

            {rankingsLoading ? (
              <div className="flex flex-col items-center justify-center py-32 animate-pulse">
                <BarChart2 size={48} className="text-[#A8C7FA] mb-4" />
                <p className="text-[#9CA3AF] font-medium tracking-wide">Compiling robust statistical rankings...</p>
              </div>
            ) : rankingsData && (
              // Changed from grid-cols-2 to a simple column layout for vertical stacking
              <div className="flex flex-col gap-10 animate-in slide-in-from-bottom-4 duration-700 w-full">
                
                {/* 🏆 Top 10 Undervalued */}
                <div className="glass-panel p-0 overflow-hidden relative w-full">
                  <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>
                  <div className="p-6 border-b border-white/10 flex items-center gap-3">
                    <Trophy className="text-emerald-400" size={28} />
                    <h3 className="text-2xl font-extrabold text-white">Top 10 Undervalued</h3>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-white/5 text-[#9CA3AF] text-xs uppercase tracking-widest">
                          <th className="py-4 px-6 font-bold w-24">Rank</th>
                          <th className="py-4 px-6 font-bold w-32">Ticker</th>
                          <th className="py-4 px-6 font-bold">Company</th>
                          <th className="py-4 px-6 font-bold text-right w-32">Z-Score</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {rankingsData.top_10.map((item, idx) => (
                          <tr key={item.symbol} onClick={() => handleSelectTicker(item.symbol)} className="hover:bg-white/5 transition-colors cursor-pointer group">
                            <td className="py-4 px-6 font-bold text-[#9CA3AF] group-hover:text-white">{idx + 1}</td>
                            <td className="py-4 px-6"><span className="text-sm font-black px-2 py-1 bg-white/5 rounded text-white tracking-widest">{item.symbol}</span></td>
                            <td className="py-4 px-6 font-semibold text-white">{item.company_name}</td>
                            <td className="py-4 px-6 font-black text-emerald-400 text-right">+{item.z_score.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* ⚠️ Bottom 10 Overvalued */}
                <div className="glass-panel p-0 overflow-hidden relative w-full">
                  <div className="absolute top-0 right-0 w-64 h-64 bg-red-500/10 rounded-full blur-3xl pointer-events-none"></div>
                  <div className="p-6 border-b border-white/10 flex items-center gap-3">
                    <AlertTriangle className="text-red-400" size={28} />
                    <h3 className="text-2xl font-extrabold text-white">Top 10 Overvalued</h3>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-white/5 text-[#9CA3AF] text-xs uppercase tracking-widest">
                          <th className="py-4 px-6 font-bold w-24">Rank</th>
                          <th className="py-4 px-6 font-bold w-32">Ticker</th>
                          <th className="py-4 px-6 font-bold">Company</th>
                          <th className="py-4 px-6 font-bold text-right w-32">Z-Score</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {rankingsData.bottom_10.map((item, idx) => (
                          <tr key={item.symbol} onClick={() => handleSelectTicker(item.symbol)} className="hover:bg-white/5 transition-colors cursor-pointer group">
                            <td className="py-4 px-6 font-bold text-[#9CA3AF] group-hover:text-white">{idx + 1}</td>
                            <td className="py-4 px-6"><span className="text-sm font-black px-2 py-1 bg-white/5 rounded text-white tracking-widest">{item.symbol}</span></td>
                            <td className="py-4 px-6 font-semibold text-white">{item.company_name}</td>
                            <td className="py-4 px-6 font-black text-red-400 text-right">{item.z_score.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}