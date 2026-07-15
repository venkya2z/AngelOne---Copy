"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import clsx from "clsx";
import { useMarket } from "@/context/MarketContext";
import { AlertCircle, RefreshCw } from "lucide-react";

// Mock Data Generator
const generateStrikes = (spot: number, step: number, count: number) => {
  const strikes = [];
  const start = Math.floor(spot / step) * step - Math.floor(count / 2) * step;
  for (let i = 0; i < count; i++) {
    strikes.push(start + i * step);
  }
  return strikes;
};

const INDICES = [
  { name: "NIFTY 50", symbol: "NIFTY", token: "99926000", fallbackSpot: 26000, step: 50 },
  { name: "BANK NIFTY", symbol: "BANKNIFTY", token: "99926009", fallbackSpot: 48000, step: 100 },
  { name: "SENSEX", symbol: "SENSEX", token: "99919000", fallbackSpot: 72000, step: 100 },
];

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState(INDICES[0]);
  const { marketData, isConnected } = useMarket();
  const [historicalPrices, setHistoricalPrices] = useState<Record<string, number>>({});
  const [loadingHistorical, setLoadingHistorical] = useState(true);

  // Fetch historical closing prices for all indices
  useEffect(() => {
    const fetchHistoricalData = async () => {
      setLoadingHistorical(true);
      const prices: Record<string, number> = {};

      for (const index of INDICES) {
        try {
          const res = await fetch(`http://127.0.0.1:8000/api/historical_spot?symbol=${index.symbol}`);
          const data = await res.json();
          if (data.status === "success" && data.last_close) {
            prices[index.symbol] = data.last_close;
          }
        } catch (err) {
          console.error(`Failed to fetch historical data for ${index.symbol}`, err);
        }
      }

      setHistoricalPrices(prices);
      setLoadingHistorical(false);
    };

    fetchHistoricalData();
  }, []);

  // Get Price Priority: 1. WebSocket Live, 2. Historical API, 3. Fallback
  const liveData = marketData[activeTab.token];
  const hasLiveData = liveData && liveData.ltp > 0;
  // State for Option Chain
  const [chainData, setChainData] = useState<any[]>([]);
  const [loadingChain, setLoadingChain] = useState(false);
  const [apiSpot, setApiSpot] = useState<number | null>(null);

  // Fetch Option Chain Structure (Backend Source of Truth)
  useEffect(() => {
    const fetchChain = async () => {
      setLoadingChain(true);
      try {
        console.log(`Fetching chain for ${activeTab.symbol}...`);
        const res = await fetch(`http://127.0.0.1:8000/api/optionchain?symbol=${activeTab.symbol}`);
        const data = await res.json();

        if (data.status === "success") {
          setChainData(data.options || []);
          setApiSpot(data.spot_price);
        } else {
          console.error("Chain fetch failed:", data);
          setChainData([]);
        }
      } catch (err) {
        console.error("Error fetching option chain:", err);
      } finally {
        setLoadingChain(false);
      }
    };

    fetchChain();
  }, [activeTab.symbol]);

  // Historical Prices: Record<string, number>
  // Access: historicalPrices[symbol] is safe if typed

  // Determine Display Spot
  const liveSpotData = marketData[activeTab.token];
  const liveSpot = liveSpotData?.ltp;

  const displaySpot = liveSpot || apiSpot || historicalPrices[activeTab.symbol] || activeTab.fallbackSpot;

  const getDataSourceLabel = () => {
    if (liveSpot) return "LIVE";
    if (apiSpot) return "SNAPSHOT";
    if (historicalPrices[activeTab.symbol]) return "HISTORICAL";
    return "FALLBACK";
  };
  const dataSource = getDataSourceLabel();

  return (
    <div className="space-y-6">
      {/* Index Tabs */}
      <div className="flex items-center gap-2 p-1 bg-card rounded-lg w-fit border border-border shadow-sm">
        {INDICES.map((index) => (
          <button
            key={index.symbol}
            onClick={() => setActiveTab(index)}
            className={clsx(
              "px-4 py-2 text-sm font-medium rounded-md transition-all relative z-10",
              activeTab.symbol === index.symbol ? "text-primary-foreground" : "text-secondary hover:text-foreground"
            )}
          >
            {activeTab.symbol === index.symbol && (
              <motion.div
                layoutId="activeTab"
                className="absolute inset-0 bg-primary rounded-md -z-10 shadow-sm"
              />
            )}
            {index.name}
          </button>
        ))}
      </div>

      {/* Spot Price Hero */}
      <div className="flex items-center justify-between bg-card p-6 rounded-xl border border-border shadow-sm">
        <div>
          <h2 className="text-secondary text-sm uppercase tracking-wider font-semibold">
            Spot Price
          </h2>
          <div className="text-5xl font-bold text-foreground font-mono mt-2 tracking-tight">
            {loadingHistorical && !displaySpot ? (
              <span className="text-secondary flex items-center gap-2 text-2xl">
                <RefreshCw className="h-6 w-6 animate-spin" />
                Initializing...
              </span>
            ) : (
              <>
                {displaySpot?.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                <span className={clsx(
                  "text-lg font-medium ml-4 relative -top-3",
                  dataSource === "LIVE" ? "text-success" : "text-warning"
                )}>
                  ● {dataSource}
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Visual Option Chain Ladder */}
      <div className="bg-card border border-border rounded-xl overflow-hidden shadow-sm">
        {/* Header */}
        <div className="grid grid-cols-3 bg-secondary/5 p-4 text-xs font-bold text-secondary uppercase text-center border-b border-border">
          <div>Call (LTP)</div>
          <div>Strike</div>
          <div>Put (LTP)</div>
        </div>

        {/* Chain Content */}
        {loadingChain ? (
          <div className="p-12 text-center text-secondary">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2" />
            Fetching Live Chain...
          </div>
        ) : chainData.length === 0 ? (
          <div className="p-8 text-center text-secondary">
            No Option Data Available. (Check Backend Logs)
          </div>
        ) : (
          <div className="max-h-[600px] overflow-auto custom-scrollbar">
            {chainData.map((row, idx) => {
              const strike = row.strike;

              // Get Live Data using Tokens
              const ceToken = row.ce_token;
              const peToken = row.pe_token;

              const ceLtp = marketData[ceToken]?.ltp || 0;
              const peLtp = marketData[peToken]?.ltp || 0;

              // DEBUG: Log first strike for troubleshooting
              if (idx === 0) {
                console.log('[DEBUG] First Strike:', {
                  strike,
                  ceToken,
                  peToken,
                  ceData: marketData[ceToken],
                  peData: marketData[peToken],
                  ceLtp,
                  peLtp,
                  marketDataKeys: Object.keys(marketData).slice(0, 10),
                  marketDataSize: Object.keys(marketData).length
                });
              }

              // Simple ATM Highlight (Closest to displaySpot)
              // Since rows are ordered, we could find min diff. 
              // For UI simplicity, just highlight the row closest to spot.
              // Let's rely on background subtle color or just checking diff
              const isATM = Math.abs(strike - displaySpot) < (activeTab.step * 0.7);

              return (
                <div
                  key={strike}
                  className={clsx(
                    "grid grid-cols-3 text-center border-b border-border/50 hover:bg-secondary/5 transition-colors cursor-pointer group",
                    isATM && "bg-primary/5 border-primary/20 relative z-0"
                  )}
                >
                  {/* CE Side */}
                  <div className={clsx("p-4 font-mono font-medium relative", "text-success")}>
                    {ceLtp > 0 ? ceLtp.toFixed(2) : <span className="text-secondary text-xs opacity-50">Waiting</span>}
                    {ceToken && <span className="absolute bottom-1 right-2 text-[10px] text-secondary/30 hidden group-hover:block">{ceToken}</span>}
                  </div>

                  {/* Strike */}
                  <div className="p-4 font-bold text-foreground bg-secondary/5 font-mono text-sm flex items-center justify-center relative border-x border-border/50">
                    {strike}
                  </div>

                  {/* PE Side */}
                  <div className={clsx("p-4 font-mono font-medium relative", "text-danger")}>
                    {peLtp > 0 ? peLtp.toFixed(2) : <span className="text-secondary text-xs opacity-50">Waiting</span>}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
