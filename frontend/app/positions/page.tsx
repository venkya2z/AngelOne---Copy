"use client";

import { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, ArrowRight, X, RefreshCw } from "lucide-react";
import clsx from "clsx";

export default function PositionsPage() {
    const [positions, setPositions] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [publishing, setPublishing] = useState(false);

    const fetchPositions = async () => {
        setLoading(true);
        try {
            const res = await fetch("http://127.0.0.1:8000/api/positions");
            const json = await res.json();

            if (json.status === "success") {
                setPositions(json.data || []);
                setError(null);
            } else {
                setError(json.error || "Failed to fetch positions");
            }
        } catch (err) {
            setError("Connection error. Is backend running?");
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

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
                // Silent success - refresh positions
                setTimeout(() => fetchPositions(), 1000);
            } else {
                alert(`❌ Error: ${json.message}`);
            }
        } catch (err) {
            alert("❌ Connection error. Is backend running?");
            console.error(err);
        } finally {
            setPublishing(false);
        }
    };

    useEffect(() => {
        fetchPositions();
    }, []);

    const totalPnL = positions.reduce((acc, pos) => acc + (parseFloat(pos.pnl || pos.unrealisedprofit || 0)), 0);

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold">Positions & P&L</h1>
                <button
                    onClick={fetchPositions}
                    className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition"
                >
                    <RefreshCw className="h-4 w-4" />
                    Refresh
                </button>
            </div>

            {/* Global P&L Card */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className={clsx(
                    "p-6 rounded-xl border flex items-center justify-between",
                    totalPnL >= 0 ? "bg-success/10 border-success/30" : "bg-danger/10 border-danger/30"
                )}>
                    <div>
                        <div className="text-secondary text-sm uppercase">Total P&L</div>
                        <div className={clsx("text-4xl font-bold font-mono mt-1", totalPnL >= 0 ? "text-success" : "text-danger")}>
                            {totalPnL >= 0 ? "+" : ""}{totalPnL.toFixed(2)}
                        </div>
                    </div>
                    {totalPnL >= 0 ? <TrendingUp className="h-12 w-12 text-success opacity-50" /> : <TrendingDown className="h-12 w-12 text-danger opacity-50" />}
                </div>

                {/* Manual Trading Controls */}
                <div className="p-6 rounded-xl border border-border bg-card flex flex-col justify-center items-start">
                    <div className="text-secondary text-sm mb-4 uppercase tracking-wider font-semibold">📡 Manual Trading</div>
                    <div className="text-xs text-secondary mb-3">Publish signals via Redis to StrategyEngine</div>
                    <div className="flex gap-2 w-full mb-2">
                        <button
                            onClick={() => publishSignal("BUY_CE")}
                            disabled={publishing}
                            className="bg-green-500 hover:bg-green-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-4 py-3 rounded-lg font-bold flex-1 transition-colors text-sm"
                        >
                            {publishing ? "⏳" : "📈"} Buy CE
                        </button>
                        <button
                            onClick={() => publishSignal("BUY_PE")}
                            disabled={publishing}
                            className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-4 py-3 rounded-lg font-bold flex-1 transition-colors text-sm"
                        >
                            {publishing ? "⏳" : "📉"} Buy PE
                        </button>
                    </div>
                    <button
                        onClick={() => publishSignal("EXIT")}
                        disabled={publishing}
                        className="bg-danger hover:bg-red-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-bold w-full transition-colors flex items-center justify-center gap-2"
                    >
                        {publishing ? "⏳ Publishing..." : "🚪 EXIT POSITION"}
                        {!publishing && <ArrowRight className="h-4 w-4" />}
                    </button>
                </div>
            </div>

            {/* Positions Table */}
            <div className="bg-card border border-border rounded-xl overflow-hidden">
                {loading ? (
                    <div className="p-12 text-center text-secondary">
                        <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2" />
                        Loading positions...
                    </div>
                ) : error ? (
                    <div className="p-12 text-center text-danger">
                        <p className="font-medium">{error}</p>
                        <p className="text-sm mt-2 text-secondary">Make sure backend is running: <code className="bg-secondary/10 px-2 py-1 rounded">python backend/main.py</code></p>
                    </div>
                ) : positions.length === 0 ? (
                    <div className="p-12 text-center text-secondary">
                        No open positions
                    </div>
                ) : (
                    <table className="w-full text-left">
                        <thead className="bg-secondary/10 text-secondary text-xs uppercase">
                            <tr>
                                <th className="p-4">Instrument</th>
                                <th className="p-4">Product</th>
                                <th className="p-4 text-right">Qty</th>
                                <th className="p-4 text-right">Avg Price</th>
                                <th className="p-4 text-right">LTP</th>
                                <th className="p-4 text-right">P&L</th>
                                <th className="p-4 text-right">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border/10 font-mono text-sm">
                            {positions.map((pos, idx) => {
                                const pnl = parseFloat(pos.pnl || pos.unrealisedprofit || 0);
                                return (
                                    <tr key={idx} className="hover:bg-secondary/5">
                                        <td className="p-4 font-bold text-foreground">{pos.tradingsymbol || pos.symboltoken}</td>
                                        <td className="p-4">
                                            <span className="bg-primary/20 text-primary text-xs px-2 py-1 rounded">{pos.producttype || 'N/A'}</span>
                                        </td>
                                        <td className="p-4 text-right">{pos.netqty || pos.buyqty}</td>
                                        <td className="p-4 text-right">{parseFloat(pos.avgprice || pos.buyavgprice || 0).toFixed(2)}</td>
                                        <td className="p-4 text-right">{parseFloat(pos.ltp || pos.close || 0).toFixed(2)}</td>
                                        <td className={clsx("p-4 text-right font-bold", pnl >= 0 ? "text-success" : "text-danger")}>
                                            {pnl >= 0 ? "+" : ""}{pnl.toFixed(2)}
                                        </td>
                                        <td className="p-4 text-right">
                                            <button className="bg-red-500/10 hover:bg-red-500/20 text-red-500 p-2 rounded-lg transition-colors" title="Exit Position">
                                                <X className="h-4 w-4" />
                                            </button>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}
