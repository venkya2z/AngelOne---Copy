"use client";

import { useState, useEffect } from "react";
import { Save, RotateCcw, AlertCircle } from "lucide-react";
import clsx from "clsx";

interface StrategyConfig {
    trading_mode: string;
    trading_index?: string;
    paper_mode_capital?: number;
    usable_funds_percent: number;
    confidence_num_lots: {
        HIGH: number;
        MEDIUM: number;
        LOW: number;
    };
    profit_booking_enabled?: boolean;
    pnl_target_per_lot: number;
    stop_loss_enabled?: boolean;
    stop_loss_per_lot: number;
    peak_detection_mode: string;
    peak_lookback_ticks: number;
}

export default function SettingsPage() {
    const [config, setConfig] = useState<StrategyConfig | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    useEffect(() => {
        fetchConfig();
    }, []);

    const fetchConfig = async () => {
        try {
            const res = await fetch("http://127.0.0.1:8000/api/strategy/config");
            const data = await res.json();
            setConfig(data);
            setLoading(false);
        } catch (err) {
            console.error("Failed to fetch config:", err);
            setLoading(false);
        }
    };

    const saveConfig = async () => {
        if (!config) return;

        setSaving(true);
        setMessage(null);

        try {
            const res = await fetch("http://127.0.0.1:8000/api/strategy/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(config)
            });

            if (res.ok) {
                setMessage({ type: 'success', text: 'Settings saved successfully!' });
            } else {
                setMessage({ type: 'error', text: 'Failed to save settings' });
            }
        } catch (err) {
            setMessage({ type: 'error', text: 'Connection error' });
        } finally {
            setSaving(false);
        }
    };

    const resetDefaults = () => {
        if (confirm("Reset all settings to default values?")) {
            setConfig({
                trading_mode: "PAPER",
                trading_index: "NIFTY",
                paper_mode_capital: 100000,
                usable_funds_percent: 50,
                confidence_num_lots: { HIGH: 5, MEDIUM: 3, LOW: 1 },
                profit_booking_enabled: true,
                pnl_target_per_lot: 500,
                stop_loss_enabled: true,
                stop_loss_per_lot: 200,
                peak_detection_mode: "MEDIUM_LOW",
                peak_lookback_ticks: 5
            });
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-foreground/70">Loading settings...</div>
            </div>
        );
    }

    if (!config) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-danger">Failed to load settings</div>
            </div>
        );
    }

    return (
        <div className="space-y-6 max-w-4xl">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold text-foreground">Strategy Settings</h1>
                <p className="text-foreground/70 mt-1 font-medium">Configure trading parameters and risk controls</p>
            </div>

            {/* Message Banner */}
            {message && (
                <div className={clsx(
                    "p-4 rounded-lg border flex items-center gap-3",
                    message.type === 'success' ? "bg-success/10 border-success/30 text-success" : "bg-danger/10 border-danger/30 text-danger"
                )}>
                    <AlertCircle className="h-5 w-5" />
                    <span>{message.text}</span>
                </div>
            )}

            {/* Trading Mode */}
            <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-foreground mb-4">Trading Mode</h2>
                <div className="flex gap-4">
                    <button
                        onClick={() => setConfig({ ...config, trading_mode: "PAPER" })}
                        className={clsx(
                            "flex-1 p-4 rounded-lg border-2 transition-all",
                            config.trading_mode === "PAPER"
                                ? "border-primary bg-primary/10 text-primary"
                                : "border-border bg-card hover:border-primary/50"
                        )}
                    >
                        <div className="font-semibold">🧪 Paper Trading</div>
                        <div className="text-sm text-foreground/70 mt-1">Simulated trades (Safe testing)</div>
                    </button>
                    <button
                        onClick={() => setConfig({ ...config, trading_mode: "LIVE" })}
                        className={clsx(
                            "flex-1 p-4 rounded-lg border-2 transition-all",
                            config.trading_mode === "LIVE"
                                ? "border-danger bg-danger/10 text-danger"
                                : "border-border bg-card hover:border-danger/50"
                        )}
                    >
                        <div className="font-semibold">🔴 Live Trading</div>
                        <div className="text-sm text-foreground/70 mt-1">Real orders (Use with caution)</div>
                    </button>
                </div>
            </div>

            {/* Trading Index Selection */}
            <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-foreground mb-4">📈 Trading Index</h2>
                <div>
                    <label className="text-sm text-foreground font-medium">
                        Select Index to Trade
                    </label>
                    <select
                        value={config.trading_index || "NIFTY"}
                        onChange={(e) => setConfig({ ...config, trading_index: e.target.value })}
                        className="w-full mt-2 px-3 py-2 bg-background border border-border rounded-lg text-foreground font-medium"
                    >
                        <option value="NIFTY">NIFTY 50</option>
                        <option value="BANKNIFTY">BANK NIFTY</option>
                        <option value="SENSEX">SENSEX</option>
                    </select>
                    <p className="text-sm text-foreground/70 mt-2">
                        Bot will trade options of the selected index. Make sure your Signal Generator is also configured for the same index.
                    </p>
                </div>
            </div>

            {/* Paper Mode Capital (only show in PAPER mode) */}
            {config.trading_mode === "PAPER" && (
                <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
                    <h2 className="text-lg font-semibold text-foreground mb-4">🧪 Paper Trading Capital</h2>
                    <div>
                        <label className="text-sm text-foreground font-medium">
                            Simulated Capital: ₹{config.paper_mode_capital?.toLocaleString('en-IN') || '1,00,000'}
                        </label>
                        <input
                            type="number"
                            min="10000"
                            max="10000000"
                            step="10000"
                            value={config.paper_mode_capital || 100000}
                            onChange={(e) => setConfig({ ...config, paper_mode_capital: parseInt(e.target.value) })}
                            className="w-full mt-2 px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                        />
                        <p className="text-sm text-foreground/70 mt-2">
                            Set your simulated account balance for paper trading. This allows testing with any capital amount.
                        </p>
                    </div>
                </div>
            )}

            {/* Usable Funds */}
            <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-foreground mb-4">💰 Usable Funds</h2>
                <div className="space-y-4">
                    <div>
                        <label className="text-sm text-foreground font-medium">
                            Percentage of Available Funds: {config.usable_funds_percent}%
                        </label>
                        <input
                            type="range"
                            min="10"
                            max="100"
                            step="5"
                            value={config.usable_funds_percent}
                            onChange={(e) => setConfig({ ...config, usable_funds_percent: parseInt(e.target.value) })}
                            className="w-full h-2 bg-secondary/20 rounded-lg appearance-none cursor-pointer mt-2"
                        />
                        <div className="flex justify-between text-xs text-foreground/60 mt-1 font-medium">
                            <span>10%</span>
                            <span>50%</span>
                            <span>100%</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Lot Sizing */}
            <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-foreground mb-4">📊 Lot Sizing (Confidence-Based)</h2>
                <div className="grid grid-cols-3 gap-4">
                    <div>
                        <label className="text-sm text-foreground font-medium">High Confidence</label>
                        <input
                            type="number"
                            min="1"
                            max="10"
                            value={config.confidence_num_lots.HIGH}
                            onChange={(e) => setConfig({
                                ...config,
                                confidence_num_lots: { ...config.confidence_num_lots, HIGH: parseInt(e.target.value) }
                            })}
                            className="w-full mt-2 px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                        />
                        <p className="text-xs text-foreground/70 mt-1">Lots for HIGH confidence signals</p>
                    </div>
                    <div>
                        <label className="text-sm text-foreground font-medium">Medium Confidence</label>
                        <input
                            type="number"
                            min="1"
                            max="10"
                            value={config.confidence_num_lots.MEDIUM}
                            onChange={(e) => setConfig({
                                ...config,
                                confidence_num_lots: { ...config.confidence_num_lots, MEDIUM: parseInt(e.target.value) }
                            })}
                            className="w-full mt-2 px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                        />
                        <p className="text-xs text-foreground/70 mt-1">Lots for MEDIUM confidence signals</p>
                    </div>
                    <div>
                        <label className="text-sm text-foreground font-medium">Low Confidence</label>
                        <input
                            type="number"
                            min="1"
                            max="10"
                            value={config.confidence_num_lots.LOW}
                            onChange={(e) => setConfig({
                                ...config,
                                confidence_num_lots: { ...config.confidence_num_lots, LOW: parseInt(e.target.value) }
                            })}
                            className="w-full mt-2 px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                        />
                        <p className="text-xs text-foreground/70 mt-1">Lots for LOW confidence signals</p>
                    </div>
                </div>
            </div>

            {/* P&L Exits - Split into two sections */}
            <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-foreground mb-4">🎯 Profit Booking</h2>
                <div className="flex items-center justify-between mb-4">
                    <span className="text-sm text-foreground/70 font-medium">Enable Profit Target Exit</span>
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={config.profit_booking_enabled ?? true}
                            onChange={(e) => setConfig({ ...config, profit_booking_enabled: e.target.checked })}
                            className="w-4 h-4"
                        />
                        <span className="text-sm text-foreground/70 font-medium">Enable</span>
                    </label>
                </div>
                <div>
                    <label className="text-sm text-foreground font-medium">Profit Target (per lot)</label>
                    <div className="relative mt-2">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground/70">₹</span>
                        <input
                            type="number"
                            min="100"
                            max="2000"
                            step="50"
                            value={config.pnl_target_per_lot}
                            onChange={(e) => setConfig({ ...config, pnl_target_per_lot: parseInt(e.target.value) })}
                            disabled={!config.profit_booking_enabled}
                            className="w-full pl-8 pr-3 py-2 bg-background border border-border rounded-lg text-foreground disabled:opacity-50"
                        />
                    </div>
                </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-foreground mb-4">🛡️ Stop Loss</h2>
                <div className="flex items-center justify-between mb-4">
                    <span className="text-sm text-foreground/70 font-medium">Enable Stop Loss Exit</span>
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={config.stop_loss_enabled ?? true}
                            onChange={(e) => setConfig({ ...config, stop_loss_enabled: e.target.checked })}
                            className="w-4 h-4"
                        />
                        <span className="text-sm text-foreground/70 font-medium">Enable</span>
                    </label>
                </div>
                <div>
                    <label className="text-sm text-foreground font-medium">Stop Loss (per lot)</label>
                    <div className="relative mt-2">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground/70">₹</span>
                        <input
                            type="number"
                            min="50"
                            max="1000"
                            step="50"
                            value={config.stop_loss_per_lot}
                            onChange={(e) => setConfig({ ...config, stop_loss_per_lot: parseInt(e.target.value) })}
                            disabled={!config.stop_loss_enabled}
                            className="w-full pl-8 pr-3 py-2 bg-background border border-border rounded-lg text-foreground disabled:opacity-50"
                        />
                    </div>
                </div>
            </div>

            {/* Peak Detection */}
            <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-foreground mb-4">📈 Peak Detection (Momentum Reversal)</h2>
                <div className="space-y-4">
                    <div>
                        <label className="text-sm text-foreground/70 font-medium">Detection Mode</label>
                        <select
                            value={config.peak_detection_mode}
                            onChange={(e) => setConfig({ ...config, peak_detection_mode: e.target.value })}
                            className="w-full mt-2 px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                        >
                            <option value="MEDIUM_LOW">Medium & Low Confidence Only (Recommended)</option>
                            <option value="ALL">All Trades</option>
                            <option value="DISABLED">Disabled</option>
                        </select>
                        <p className="text-xs text-foreground/70 mt-2">
                            {config.peak_detection_mode === "MEDIUM_LOW" && "HIGH confidence trades ride longer. MEDIUM/LOW lock profits early."}
                            {config.peak_detection_mode === "ALL" && "All trades exit on momentum reversal."}
                            {config.peak_detection_mode === "DISABLED" && "Peak detection disabled for all trades."}
                        </p>
                    </div>
                    <div>
                        <label className="text-sm text-foreground/70 font-medium">
                            Lookback Window: {config.peak_lookback_ticks} ticks
                        </label>
                        <input
                            type="range"
                            min="3"
                            max="10"
                            value={config.peak_lookback_ticks}
                            onChange={(e) => setConfig({ ...config, peak_lookback_ticks: parseInt(e.target.value) })}
                            disabled={config.peak_detection_mode === "DISABLED"}
                            className="w-full h-2 bg-secondary/20 rounded-lg appearance-none cursor-pointer mt-2 disabled:opacity-50"
                        />
                    </div>
                </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-4">
                <button
                    onClick={saveConfig}
                    disabled={saving}
                    className="flex-1 bg-primary text-primary-foreground px-6 py-3 rounded-lg font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                    <Save className="h-5 w-5" />
                    {saving ? "Saving..." : "Save Changes"}
                </button>
                <button
                    onClick={resetDefaults}
                    className="px-6 py-3 bg-secondary/20 text-foreground rounded-lg font-semibold hover:bg-secondary/30 transition-colors flex items-center gap-2"
                >
                    <RotateCcw className="h-5 w-5" />
                    Reset to Defaults
                </button>
            </div>

            {/* Restart Notice */}
            {config.trading_mode === "LIVE" && (
                <div className="bg-warning/10 border border-warning/30 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                        <AlertCircle className="h-5 w-5 text-warning flex-shrink-0 mt-0.5" />
                        <div>
                            <p className="font-semibold text-warning">Changing to LIVE mode requires backend restart</p>
                            <p className="text-sm text-foreground/70 mt-1">
                                After saving, restart the backend using <code className="bg-background px-1 rounded">restart_bot.bat</code>
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
