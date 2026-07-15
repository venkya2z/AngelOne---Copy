"use client";

import { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, RefreshCw, AlertCircle, History, ArrowRight } from "lucide-react";
import clsx from "clsx";

export default function PaperDashboard() {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [publishing, setPublishing] = useState(false);

    const publishSignal = async (action: string) => {
        if (publishing) return;

        setPublishing(true);
        try {
            const res = await fetch("http://127.0.0.1:8000/api/publish-signal", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action })
            });

            const json = await res.json();

            if (json.status === "success") {
                // Silent success - refresh data
                // Refresh data after 1 second to see the new trade
                setTimeout(() => fetchPaperData(), 1000);
            } else {
                alert(`❌ Error: ${json.message}`);
            }
        } catch (err) {
            alert("❌ Connection error. Is backend running?");
        } finally {
            setPublishing(false);
        }
    };

    const fetchPaperData = async () => {
        setLoading(true);
        try {
            const res = await fetch("http://127.0.0.1:8000/api/paper/trades");
            const json = await res.json();

            if (json.status === "success") {
                setData(json);
                setError(null);
            } else {
                setError(json.error || "Failed to fetch paper trades");
            }
        } catch (err) {
            setError("Connection error. Is backend running?");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPaperData();
        // Auto-refresh every 5 seconds only if active position exists
        const interval = setInterval(() => {
            if (data?.active_position) {
                fetchPaperData();
            }
        }, 5000);
        return () => clearInterval(interval);
    }, [data?.active_position]);

    const activePos = data?.active_position;
    const history = data?.trade_history || [];

    // Calculate Stats
    const totalTrades = history.length;
    const totalPnL = history.reduce((acc: number, trade: any) => acc + (trade.pnl || 0), 0);

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold flex items-center gap-2">
                    <span className="text-primary">🧪</span> Paper Trading Dashboard
                </h1>
                <button
                    onClick={fetchPaperData}
                    className="flex items-center gap-2 px-4 py-2 bg-secondary/10 hover:bg-secondary/20 rounded-lg transition"
                >
                    <RefreshCw className={clsx("h-4 w-4", loading && "animate-spin")} />
                    Refresh
                </button>
            </div>

            {error && (
                <div className="p-4 bg-danger/10 text-danger rounded-lg flex items-center gap-2">
                    <AlertCircle className="h-5 w-5" />
                    {error}
                </div>
            )}

            {/* MANUAL TRADING CONTROLS */}
            <div className="p-6 rounded-xl border border-border bg-card flex flex-col md:flex-row items-center justify-between gap-4">
                <div className="flex flex-col">
                    <div className="text-secondary text-sm uppercase tracking-wider font-semibold">📡 Manual Trading</div>
                    <div className="text-xs text-secondary">Publish signals via Redis to StrategyEngine</div>
                </div>

                <div className="flex items-center gap-3 w-full md:w-auto">
                    <button
                        onClick={() => publishSignal("BUY_CE")}
                        disabled={publishing}
                        className="bg-green-500 hover:bg-green-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-bold transition-colors text-sm flex-1 md:flex-none whitespace-nowrap"
                    >
                        {publishing ? "⏳" : "📈"} Buy CE
                    </button>
                    <button
                        onClick={() => publishSignal("BUY_PE")}
                        disabled={publishing}
                        className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-bold transition-colors text-sm flex-1 md:flex-none whitespace-nowrap"
                    >
                        {publishing ? "⏳" : "📉"} Buy PE
                    </button>

                    <button
                        onClick={() => publishSignal("ADD_LOT")}
                        disabled={publishing || !activePos}
                        className="bg-purple-500 hover:bg-purple-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-bold transition-colors text-sm flex-1 md:flex-none flex items-center justify-center gap-2 whitespace-nowrap"
                    >
                        {publishing ? "⏳..." : "➕ ADD LOT"}
                    </button>

                    <button
                        onClick={() => publishSignal("EXIT")}
                        disabled={publishing || !activePos}
                        className="bg-danger hover:bg-red-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-bold transition-colors text-sm flex-1 md:flex-none flex items-center justify-center gap-2 whitespace-nowrap"
                    >
                        {publishing ? "⏳..." : "🚪 EXIT"}
                    </button>
                </div>
            </div>

            {/* ACTIVE POSITION CARD */}
            {activePos ? (
                <div className="p-6 rounded-xl border border-primary/20 bg-primary/5 shadow-sm relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-2 text-[10px] font-bold uppercase tracking-wider text-primary bg-primary/10 rounded-bl-xl">
                        Live Simulation
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                        <div>
                            <div className="text-secondary text-xs uppercase mb-1">Instrument</div>
                            <div className="text-xl font-bold text-foreground">{activePos.symbol || activePos.tradingsymbol}</div>
                            <div className="text-xs text-secondary mt-1">
                                {activePos.confidence && <span className="bg-primary/10 text-primary px-1.5 py-0.5 rounded text-[10px] font-bold mr-1">{activePos.confidence}</span>}
                                {activePos.direction}
                            </div>
                        </div>

                        <div>
                            <div className="text-secondary text-xs uppercase mb-1">Lots × Size</div>
                            <div className="text-xl font-mono font-bold">
                                {activePos.num_lots ?? '?'} <span className="text-secondary text-sm">× {activePos.lot_size ?? '?'}</span>
                            </div>
                            <div className="text-xs text-secondary mt-1">
                                Qty: {activePos.quantity}
                                {(activePos.add_count > 0) && <span className="ml-1 text-purple-400">(+{activePos.add_count} adds)</span>}
                            </div>
                        </div>

                        <div>
                            <div className="text-secondary text-xs uppercase mb-1">Entry → LTP</div>
                            <div className="text-xl font-mono">
                                <span className="opacity-70">{activePos.entry_price?.toFixed(2)}</span>
                                <span className="mx-1 text-secondary">→</span>
                                <span className={clsx(activePos.ltp > activePos.entry_price ? "text-success" : "text-danger")}>
                                    {activePos.ltp?.toFixed(2) || '—'}
                                </span>
                            </div>
                        </div>

                        <div>
                            <div className="text-secondary text-xs uppercase mb-1">Unrealized P&L</div>
                            <div className={clsx("text-3xl font-bold font-mono", activePos.pnl >= 0 ? "text-success" : "text-danger")}>
                                {activePos.pnl >= 0 ? "+" : ""}₹{activePos.pnl?.toFixed(2)}
                            </div>
                        </div>
                    </div>
                </div>
            ) : (
                <div className="p-8 rounded-xl border border-dashed border-border text-center text-secondary">
                    No active paper position currently running.
                </div>
            )}

            {/* TRADE HISTORY */}
            <div className="bg-card border border-border rounded-xl overflow-hidden(shadow-sm)">
                <div className="p-4 border-b border-border bg-secondary/5 flex items-center gap-2">
                    <History className="h-4 w-4 text-secondary" />
                    <h2 className="font-semibold text-sm uppercase tracking-wider text-secondary">Session History</h2>
                    <span className="ml-auto text-xs bg-secondary/10 px-2 py-1 rounded-full">{totalTrades} Orders</span>
                </div>

                {history.length === 0 ? (
                    <div className="p-8 text-center text-secondary text-sm">No trade history found in logs this session.</div>
                ) : (
                    <div className="max-h-[400px] overflow-auto custom-scrollbar">
                        <table className="w-full text-left">
                            <thead className="bg-secondary/5 text-xs text-secondary uppercase sticky top-0 backdrop-blur-md">
                                <tr>
                                    <th className="p-3">Time</th>
                                    <th className="p-3">Symbol</th>
                                    <th className="p-3 text-right">Qty</th>
                                    <th className="p-3 text-right">Entry / Exit</th>
                                    <th className="p-3 text-right">P&L</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border/10">
                                {history.map((trade: any, idx: number) => {
                                    const pnl = trade.pnl || 0;
                                    const isWin = pnl >= 0;

                                    return (
                                        <tr key={idx} className="hover:bg-secondary/5 font-mono text-xs">
                                            <td className="p-3 text-secondary">
                                                {trade.timestamp
                                                    ? new Date(trade.timestamp * 1000).toLocaleTimeString()
                                                    : "-"}
                                            </td>
                                            <td className="p-3 font-medium">
                                                {trade.tradingsymbol || trade.symbol || "Unknown"}
                                            </td>
                                            <td className="p-3 text-right text-secondary">
                                                {trade.quantity}
                                            </td>
                                            <td className="p-3 text-right text-secondary">
                                                <span className="opacity-70">{trade.entry_price?.toFixed(2)}</span>
                                                <span className="mx-1">→</span>
                                                <span className="font-bold">{trade.exit_price?.toFixed(2)}</span>
                                            </td>
                                            <td className={clsx("p-3 text-right font-bold", isWin ? "text-success" : "text-danger")}>
                                                {isWin ? "+" : ""}{pnl.toFixed(2)}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
