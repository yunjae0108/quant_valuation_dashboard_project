"use client";

import { useState } from "react";

export default function Home() {
  const [activeTab, setActiveTab] = useState("Valuation Terminal");
  
  // Robust baseline ticker list to prevent browser CORS and fetch blocks
  const [tickers] = useState([
    { symbol: "AAPL", title: "Apple Inc." },
    { symbol: "MSFT", title: "Microsoft Corporation" },
    { symbol: "AMZN", title: "Amazon.com, Inc." },
    { symbol: "GOOGL", title: "Alphabet Inc." },
    { symbol: "TSLA", title: "Tesla, Inc." },
    { symbol: "META", title: "Meta Platforms, Inc." },
    { symbol: "NVDA", title: "NVIDIA Corporation" },
    { symbol: "NFLX", title: "Netflix, Inc." },
    { symbol: "AMD", title: "Advanced Micro Devices, Inc." },
    { symbol: "INTC", title: "Intel Corporation" },
  ]);

  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [valuationData, setValuationData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleNameChange = (name: string) => {
    setSelectedName(name);
    const found = tickers.find((t) => t.title === name);
    if (found) {
      setSelectedTicker(found.symbol);
      fetchValuation(found.symbol);
    }
  };

  const handleTickerChange = (ticker: string) => {
    setSelectedTicker(ticker);
    const found = tickers.find((t) => t.symbol === ticker);
    if (found) {
      setSelectedName(found.title);
    }
    fetchValuation(ticker);
  };

  const fetchValuation = async (ticker: string) => {
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/manual-valuation/${ticker}`);
      if (res.ok) {
        const data = await res.json();
        setValuationData(data);
      } else {
        // Fallback mock valuation data if FastAPI backend is not active yet
        setValuationData({
          company_name: tickers.find(t => t.symbol === ticker)?.title || ticker,
          price: 150.00,
          metrics: { PE_Ratio: 25.5, PB_Ratio: 5.2, EV_EBITDA: 18.4, ROE: 0.22 }
        });
      }
    } catch (e) {
      // Offline fallback for seamless frontend testing
      setValuationData({
        company_name: tickers.find(t => t.symbol === ticker)?.title || ticker,
        price: 150.00,
        metrics: { PE_Ratio: 25.5, PB_Ratio: 5.2, EV_EBITDA: 18.4, ROE: 0.22 }
      });
    } finally {
      setLoading(false);
    }
  };

  const menuItems = [
    { name: "Valuation Terminal", icon: "🔍" },
    { name: "Market Rankings", icon: "🏆" },
    { name: "Options & Volatility", icon: "📉" },
    { name: "AI Predictive Modeling", icon: "🤖" },
  ];

  return (
    <div className="flex h-screen bg-[#0B0E14] text-[#E2E2E2] overflow-hidden">
      
      {/* Sidebar Navigation */}
      <aside className="w-72 bg-[#161A23] border-r border-white/5 flex flex-col z-20 shadow-2xl">
        <div className="p-8 mb-4">
          <h1 className="text-3xl font-extrabold text-[#A8C7FA] tracking-tight">
            Quant Engine
          </h1>
        </div>
        
        <nav className="flex-1 px-4 space-y-2">
          {menuItems.map((item) => (
            <button
              key={item.name}
              onClick={() => setActiveTab(item.name)}
              className={`w-full flex items-center gap-4 px-5 py-4 rounded-xl text-left transition-all duration-200 cursor-pointer ${
                activeTab === item.name
                  ? "bg-[#A8C7FA]/10 border-l-4 border-[#A8C7FA] shadow-lg transform translate-x-1"
                  : "border-l-4 border-transparent hover:bg-white/5"
              }`}
            >
              <span className={`text-2xl ${activeTab === item.name ? "opacity-100" : "opacity-70"}`}>
                {item.icon}
              </span>
              <span className={`text-[1.1rem] ${activeTab === item.name ? "text-[#FFFFFF] font-bold" : "text-[#9CA3AF] font-medium"}`}>
                {item.name}
              </span>
            </button>
          ))}
        </nav>
        
        <div className="p-6 border-t border-white/5 bg-[#0B0E14]/30">
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.6)]"></div>
            <span className="text-sm font-semibold text-[#9CA3AF] tracking-wide uppercase">System Online</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 p-12 overflow-y-auto relative">
        <div className="absolute top-0 left-0 w-full h-96 bg-[#A8C7FA]/5 blur-[120px] -z-10 pointer-events-none"></div>

        <header className="mb-8">
          <h2 className="text-4xl font-extrabold tracking-tight text-gradient inline-block pb-2">
            {activeTab}
          </h2>
        </header>

        {activeTab === "Valuation Terminal" && (
          <div className="space-y-8 animate-in fade-in duration-300">
            {/* Split Search Bar Interface */}
            <div className="glass-panel p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-semibold text-[#A8C7FA] mb-2 uppercase tracking-wider">
                  Search by Company Name
                </label>
                <select
                  className="w-full bg-[#0B0E14] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-[#A8C7FA]"
                  value={selectedName || ""}
                  onChange={(e) => handleNameChange(e.target.value)}
                >
                  <option value="" disabled>Select Company Name...</option>
                  {tickers.map((t) => (
                    <option key={t.symbol} value={t.title}>{t.title}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold text-[#A8C7FA] mb-2 uppercase tracking-wider">
                  Search by Ticker Symbol
                </label>
                <select
                  className="w-full bg-[#0B0E14] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-[#A8C7FA]"
                  value={selectedTicker || ""}
                  onChange={(e) => handleTickerChange(e.target.value)}
                >
                  <option value="" disabled>Select Ticker...</option>
                  {tickers.map((t) => (
                    <option key={t.symbol} value={t.symbol}>{t.symbol} - {t.title}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Valuation Results Display */}
            {loading && (
              <div className="glass-panel p-12 text-center text-[#9CA3AF] animate-pulse">
                Aggregating quantitative financial data...
              </div>
            )}

            {valuationData && !loading && (
              <div className="glass-panel p-8 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="flex justify-between items-center border-b border-white/5 pb-4">
                  <h3 className="text-2xl font-bold text-white">
                    🏢 {valuationData.company_name} <span className="text-[#A8C7FA]">({selectedTicker})</span>
                  </h3>
                  <div className="text-3xl font-extrabold text-white">
                    ${valuationData.price?.toFixed(2)}
                  </div>
                </div>

                {/* Metrics Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-[#0B0E14] p-5 rounded-xl border border-white/5">
                    <div className="text-xs font-semibold text-[#A8C7FA] uppercase mb-1">P/E Ratio</div>
                    <div className="text-2xl font-bold text-white">
                      {valuationData.metrics?.PE_Ratio?.toFixed(2) || "N/A"}
                    </div>
                  </div>
                  <div className="bg-[#0B0E14] p-5 rounded-xl border border-white/5">
                    <div className="text-xs font-semibold text-[#A8C7FA] uppercase mb-1">P/B Ratio</div>
                    <div className="text-2xl font-bold text-white">
                      {valuationData.metrics?.PB_Ratio?.toFixed(2) || "N/A"}
                    </div>
                  </div>
                  <div className="bg-[#0B0E14] p-5 rounded-xl border border-white/5">
                    <div className="text-xs font-semibold text-[#A8C7FA] uppercase mb-1">EV / EBITDA</div>
                    <div className="text-2xl font-bold text-white">
                      {valuationData.metrics?.EV_EBITDA?.toFixed(2) || "N/A"}
                    </div>
                  </div>
                  <div className="bg-[#0B0E14] p-5 rounded-xl border border-white/5">
                    <div className="text-xs font-semibold text-[#A8C7FA] uppercase mb-1">ROE</div>
                    <div className="text-2xl font-bold text-white">
                      {valuationData.metrics?.ROE ? `${(valuationData.metrics.ROE * 100).toFixed(2)}%` : "N/A"}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab !== "Valuation Terminal" && (
          <div className="glass-panel p-10">
            <h3 className="text-3xl font-bold text-white mb-4">Module Under Construction</h3>
            <p className="text-lg text-[#9CA3AF]">
              The quantitative data pipelines for {activeTab} are currently being integrated.
            </p>
          </div>
        )}
      </main>

    </div>
  );
}