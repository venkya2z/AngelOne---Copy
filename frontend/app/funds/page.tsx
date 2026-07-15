"use client";

import { useState, useEffect } from "react";
import { Wallet, PieChart, ShieldCheck, RefreshCw, AlertTriangle, Cpu } from "lucide-react";

export default function FundsPage() {
    const [fundsData, setFundsData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchFunds = async () => {
        setLoading(true);
        try {
            const res = await fetch("http://127.0.0.1:8000/api/funds");
            const json = await res.json();

            if (json.status === "success") {
                setFundsData(json.data);
                setError(null);
            } else {
                setError(json.error || "Failed to fetch funds");
            }
        } catch (err) {
            setError("Connection error. Is backend running?");
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchFunds();
    }, []);

    // Get live & paper data
    const live = fundsData?.live;
    const paper = fundsData?.paper;

    // Calculations
    const liveAvailable = live?.available_cash ? parseFloat(live.available_cash) : 0;
    const liveUsed = live?.used_margin ? parseFloat(live.used_margin) : 0;
    const liveUtilPercent = liveAvailable > 0 ? ((liveUsed / liveAvailable) * 100).toFixed(1) : "0.0";

    const paperAvailable = paper?.available_cash ? parseFloat(paper.available_cash) : 0;
    const paperUsed = paper?.used_margin ? parseFloat(paper.used_margin) : 0;
    const paperUtilPercent = paperAvailable > 0 ? ((paperUsed / paperAvailable) * 100).toFixed(1) : "0.0";

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Funds & Margin</h1>
                    <p className="text-sm text-foreground/60 mt-1">Compare Live Account funds with Paper Trading limits side-by-side</p>
                </div>
                <button
                    onClick={fetchFunds}
                    className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition shadow-sm"
                >
                    <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                    Refresh
                </button>
            </div>

            {loading && !fundsData ? (
                <div className="p-12 text-center text-foreground/70">
                    <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2 text-primary" />
                    Loading funds data...
                </div>
            ) : error ? (
                <div className="p-12 text-center text-danger bg-danger/5 border border-danger/20 rounded-xl">
                    <p className="font-medium text-lg">{error}</p>
                    <p className="text-sm mt-2 text-foreground/70">
                        Make sure your backend is running: <code className="bg-secondary/10 px-2 py-1 rounded">python backend/main.py</code>
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    
                    {/* COLUMN 1: LIVE ANGEL ONE ACCOUNT */}
                    <div className="space-y-6">
                        <div className="flex items-center gap-2 pb-2 border-b border-border">
                            <span className="h-3 w-3 rounded-full bg-red-500 animate-pulse"></span>
                            <h2 className="text-lg font-bold">🔴 Live Broker Account (Angel One)</h2>
                        </div>

                        {live && !live.status ? (
                            <div className="bg-warning/10 border border-warning/30 text-warning p-5 rounded-xl space-y-2">
                                <div className="flex items-center gap-2 font-bold text-sm">
                                    <AlertTriangle className="h-5 w-5" />
                                    Broker API Return Code / Message:
                                </div>
                                <p className="text-xs font-mono bg-warning/5 p-3 rounded border border-warning/10 max-h-24 overflow-auto">
                                    {live.message}
                                </p>
                                <p className="text-xs text-foreground/60 mt-2">
                                    Note: Some accounts do not permit direct RMS Limit queries via the API. This does not impact order placement.
                                </p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="bg-card p-5 rounded-xl border border-border">
                                    <div className="flex items-center gap-3 mb-2">
                                        <div className="p-2 bg-primary/10 rounded-lg text-primary">
                                            <Wallet className="h-5 w-5" />
                                        </div>
                                        <span className="text-foreground/75 text-sm font-medium">Available Cash</span>
                                    </div>
                                    <div className="text-2xl font-bold font-mono">
                                        ₹{liveAvailable.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                                    </div>
                                </div>

                                <div className="bg-card p-5 rounded-xl border border-border">
                                    <div className="flex items-center gap-3 mb-2">
                                        <div className="p-2 bg-warning/10 rounded-lg text-warning">
                                            <PieChart className="h-5 w-5" />
                                        </div>
                                        <span className="text-foreground/75 text-sm font-medium">Used Margin</span>
                                    </div>
                                    <div className="text-2xl font-bold font-mono">
                                        ₹{liveUsed.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                                    </div>
                                    <div className="mt-1 text-xs text-foreground/60">{liveUtilPercent}% Utilized</div>
                                </div>

                                <div className="bg-card p-5 rounded-xl border border-border md:col-span-2">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <div className="p-2 bg-success/10 rounded-lg text-success">
                                                <ShieldCheck className="h-5 w-5" />
                                            </div>
                                            <span className="text-foreground/75 text-sm font-medium">Live Account Status</span>
                                        </div>
                                        <span className="px-3 py-1 bg-success/15 text-success rounded-full text-xs font-semibold">Active</span>
                                    </div>
                                </div>
                            </div>
                        )}

                        {live && live.raw && Object.keys(live.raw).length > 0 && (
                            <div className="bg-card border border-border rounded-xl p-5 space-y-3">
                                <h3 className="font-bold text-sm text-foreground/70">Raw Live RMS Response</h3>
                                <div className="bg-secondary/5 rounded-lg p-3 font-mono text-[11px] overflow-auto max-h-48">
                                    <pre>{JSON.stringify(live.raw, null, 2)}</pre>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* COLUMN 2: SIMULATED PAPER TRADING ACCOUNT */}
                    <div className="space-y-6">
                        <div className="flex items-center gap-2 pb-2 border-b border-border">
                            <span className="h-3 w-3 rounded-full bg-primary"></span>
                            <h2 className="text-lg font-bold">🧪 Paper Trading Account (Simulated)</h2>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="bg-card p-5 rounded-xl border border-border">
                                <div className="flex items-center gap-3 mb-2">
                                    <div className="p-2 bg-primary/10 rounded-lg text-primary">
                                        <Wallet className="h-5 w-5" />
                                    </div>
                                    <span className="text-foreground/75 text-sm font-medium">Available Cash</span>
                                </div>
                                <div className="text-2xl font-bold font-mono text-primary">
                                    ₹{paperAvailable.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                                </div>
                            </div>

                            <div className="bg-card p-5 rounded-xl border border-border">
                                <div className="flex items-center gap-3 mb-2">
                                    <div className="p-2 bg-warning/10 rounded-lg text-warning">
                                        <PieChart className="h-5 w-5" />
                                    </div>
                                    <span className="text-foreground/75 text-sm font-medium">Used Margin</span>
                                </div>
                                <div className="text-2xl font-bold font-mono">
                                    ₹{paperUsed.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                                </div>
                                <div className="mt-1 text-xs text-foreground/60">{paperUtilPercent}% Utilized</div>
                            </div>

                            <div className="bg-card p-5 rounded-xl border border-border md:col-span-2">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-primary/10 rounded-lg text-primary">
                                            <Cpu className="h-5 w-5" />
                                        </div>
                                        <span className="text-foreground/75 text-sm font-medium">Paper Account Status</span>
                                    </div>
                                    <span className="px-3 py-1 bg-primary/15 text-primary rounded-full text-xs font-semibold">Active (Simulated)</span>
                                </div>
                            </div>
                        </div>

                        <div className="bg-secondary/5 border border-border rounded-xl p-5 text-sm text-foreground/70">
                            <p className="font-semibold text-foreground mb-1">About Paper Trading Funds</p>
                            These funds are fully simulated in local system memory. You can configure this starting value by changing the <code className="bg-secondary/15 px-1 py-0.5 rounded font-mono text-xs">paper_mode_capital</code> parameter inside your <code className="bg-secondary/15 px-1 py-0.5 rounded font-mono text-xs">strategy_config.json</code> configuration file.
                        </div>
                    </div>

                </div>
            )}
        </div>
    );
}
