"use client";

import { useState, useEffect } from "react";
import { Mail, TestTube, AlertCircle, Check, X } from "lucide-react";

interface EmailConfig {
    alerts_enabled: boolean;
    smtp_server: string;
    smtp_port: number;
    sender_email: string;
    sender_password: string;
    recipients: string[];
    alert_on_entry: boolean;
    alert_on_exit: boolean;
    alert_on_errors: boolean;
}

export default function EmailAlertsPage() {
    const [config, setConfig] = useState<EmailConfig | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
    const [newRecipient, setNewRecipient] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [testResult, setTestResult] = useState<string>("");
    const [sendingTest, setSendingTest] = useState(false);

    useEffect(() => {
        fetchConfig();
    }, []);

    const fetchConfig = async () => {
        try {
            const response = await fetch('http://127.0.0.1:8000/api/email/config');
            const data = await response.json();
            setConfig(data);
        } catch (error) {
            console.error('Error fetching config:', error);
            setMessage({ type: 'error', text: 'Failed to load email configuration' });
        } finally {
            setLoading(false);
        }
    };

    const saveConfig = async () => {
        if (!config) return;

        setSaving(true);
        setMessage(null);

        try {
            const response = await fetch('http://127.0.0.1:8000/api/email/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });

            if (response.ok) {
                setMessage({ type: 'success', text: 'Email settings saved successfully!' });
            } else {
                setMessage({ type: 'error', text: 'Failed to save settings' });
            }
        } catch (error) {
            setMessage({ type: 'error', text: 'Network error while saving' });
        } finally {
            setSaving(false);
        }
    };

    const testConnection = async () => {
        setTesting(true);
        setMessage(null);
        setTestResult("");

        try {
            const response = await fetch('http://127.0.0.1:8000/api/email/test');
            const data = await response.json();

            setTestResult(JSON.stringify(data, null, 2));

            if (data.success) {
                setMessage({ type: 'success', text: data.message });
            } else {
                setMessage({ type: 'error', text: data.message });
            }
        } catch (error) {
            const errorMsg = error instanceof Error ? error.message : 'Unknown error';
            setTestResult(`Network Error: ${errorMsg}`);
            setMessage({ type: 'error', text: 'Failed to test connection - Backend not running?' });
        } finally {
            setTesting(false);
        }
    };

    const sendTestEmail = async () => {
        setSendingTest(true);
        setMessage(null);

        try {
            const response = await fetch('http://127.0.0.1:8000/api/email/send-test', {
                method: 'POST'
            });
            const data = await response.json();

            if (data.success) {
                setMessage({ type: 'success', text: data.message });
            } else {
                setMessage({ type: 'error', text: data.message });
            }
        } catch (error) {
            setMessage({ type: 'error', text: 'Failed to send test email' });
        } finally {
            setSendingTest(false);
        }
    };

    const addRecipient = () => {
        if (!config || !newRecipient.trim()) return;

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(newRecipient.trim())) {
            setMessage({ type: 'error', text: 'Invalid email address' });
            return;
        }

        if (config.recipients.includes(newRecipient.trim())) {
            setMessage({ type: 'error', text: 'Email already in list' });
            return;
        }

        setConfig({
            ...config,
            recipients: [...config.recipients, newRecipient.trim()]
        });
        setNewRecipient("");
        setMessage(null);
    };

    const removeRecipient = (email: string) => {
        if (!config) return;
        setConfig({
            ...config,
            recipients: config.recipients.filter(e => e !== email)
        });
    };

    if (loading) {
        return (
            <div className="p-12 text-center">
                <div className="text-foreground/70">Loading email settings...</div>
            </div>
        );
    }

    if (!config) return null;

    return (
        <div className="p-8 max-w-4xl mx-auto">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-foreground flex items-center gap-3">
                    <Mail className="h-8 w-8" />
                    Email Alerts Configuration
                </h1>
                <p className="text-foreground/70 mt-2 font-medium">
                    Receive real-time trade notifications via email with Paper/Live mode distinction
                </p>
            </div>

            {message && (
                <div className={`mb-6 p-4 rounded-lg border ${message.type === 'success'
                    ? 'bg-green-50 border-green-200 text-green-800'
                    : 'bg-red-50 border-red-200 text-red-800'
                    }`}>
                    <div className="flex items-center gap-2">
                        {message.type === 'success' ? <Check className="h-5 w-5" /> : <X className="h-5 w-5" />}
                        <span>{message.text}</span>
                    </div>
                </div>
            )}

            <div className="bg-card border border-border rounded-xl p-6 shadow-sm mb-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-lg font-semibold text-foreground mb-1">Enable Email Alerts</h2>
                        <p className="text-sm text-foreground/70">Turn on to receive trade notifications</p>
                    </div>
                    <label className="flex items-center gap-3 cursor-pointer bg-gray-700 p-3 rounded-lg border border-gray-600 hover:bg-gray-600 transition-colors">
                        <input
                            type="checkbox"
                            checked={config.alerts_enabled}
                            onChange={(e) => setConfig({ ...config, alerts_enabled: e.target.checked })}
                            className="w-5 h-5 accent-blue-500"
                        />
                        <div className="flex flex-col">
                            <span className={`text-sm font-bold ${config.alerts_enabled ? "text-green-400" : "text-gray-300"}`}>
                                {config.alerts_enabled ? "● System Active" : "○ System Paused"}
                            </span>
                        </div>
                    </label>
                </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-6 shadow-sm mb-6">
                <h2 className="text-lg font-semibold text-foreground mb-4">📧 Gmail SMTP Setup</h2>

                <div className="space-y-4">
                    <div>
                        <label className="text-sm text-foreground font-medium">Sender Email (Gmail)</label>
                        <input
                            type="email"
                            value={config.sender_email}
                            onChange={(e) => setConfig({ ...config, sender_email: e.target.value })}
                            placeholder="your-email@gmail.com"
                            className="w-full mt-2 px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                        />
                    </div>

                    <div>
                        <label className="text-sm text-foreground font-medium">Gmail App Password</label>
                        <div className="relative mt-2">
                            <input
                                type={showPassword ? "text" : "password"}
                                value={config.sender_password}
                                onChange={(e) => setConfig({ ...config, sender_password: e.target.value })}
                                placeholder="xxxx xxxx xxxx xxxx"
                                className="w-full px-3 py-2 pr-24 bg-background border border-border rounded-lg text-foreground font-mono"
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1 text-xs bg-secondary/20 hover:bg-secondary/30 rounded"
                            >
                                {showPassword ? "Hide" : "Show"}
                            </button>
                        </div>
                        <p className="text-xs text-foreground/70 mt-2">
                            <a
                                href="https://support.google.com/accounts/answer/185833"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary hover:underline"
                            >
                                Create App Password →
                            </a>
                            {" "}Don't use your regular Gmail password!
                        </p>
                    </div>

                    <div className="flex gap-2">
                        <button
                            onClick={testConnection}
                            disabled={testing || !config.sender_email || !config.sender_password}
                            className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium"
                        >
                            <TestTube className="h-4 w-4" />
                            {testing ? "Testing..." : "Test Connection"}
                        </button>

                        <button
                            onClick={sendTestEmail}
                            disabled={sendingTest || !config.sender_email || !config.sender_password || config.recipients.length === 0}
                            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium"
                        >
                            <Mail className="h-4 w-4" />
                            {sendingTest ? "Sending..." : "Send Test Email"}
                        </button>
                    </div>

                    <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <p className="text-xs text-yellow-800">
                            ⚠️ <strong>Steps:</strong> 1) Click "Save Settings" below, 2) Test Connection, 3) Send Test Email to verify delivery
                        </p>
                    </div>

                    {testResult && (
                        <div className="mt-4 p-4 bg-background border border-border rounded-lg">
                            <h3 className="text-sm font-semibold text-foreground mb-2">Test Result:</h3>
                            <pre className="text-xs text-foreground/70 overflow-auto max-h-40 whitespace-pre-wrap font-mono">
                                {testResult}
                            </pre>
                        </div>
                    )}
                </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-6 shadow-sm mb-6">
                <h2 className="text-lg font-semibold text-foreground mb-4">📬 Alert Recipients</h2>

                <div className="mb-4">
                    <div className="flex gap-2">
                        <input
                            type="email"
                            value={newRecipient}
                            onChange={(e) => setNewRecipient(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && addRecipient()}
                            placeholder="email@example.com"
                            className="flex-1 px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                        />
                        <button
                            onClick={addRecipient}
                            disabled={!newRecipient.trim()}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                        >
                            Add
                        </button>
                    </div>
                </div>

                <div className="space-y-2">
                    {config.recipients.length === 0 ? (
                        <p className="text-sm text-foreground/70 py-4 text-center">No recipients added yet</p>
                    ) : (
                        config.recipients.map((email, idx) => (
                            <div key={idx} className="flex items-center justify-between p-3 bg-background rounded-lg border border-border">
                                <span className="text-foreground">{email}</span>
                                <button
                                    onClick={() => removeRecipient(email)}
                                    className="text-red-500 hover:text-red-700 p-1 hover:bg-red-50 rounded"
                                    title="Remove recipient"
                                >
                                    <X className="h-5 w-5" />
                                </button>
                            </div>
                        ))
                    )}
                </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-6 shadow-sm mb-6">
                <h2 className="text-lg font-semibold text-foreground mb-4">🔔 Alert Types</h2>

                <div className="space-y-3">
                    <label className="flex items-center justify-between p-3 bg-background rounded-lg border border-border cursor-pointer">
                        <span className="text-foreground">Trade Entry Alerts</span>
                        <input
                            type="checkbox"
                            checked={config.alert_on_entry}
                            onChange={(e) => setConfig({ ...config, alert_on_entry: e.target.checked })}
                            className="w-4 h-4"
                        />
                    </label>

                    <label className="flex items-center justify-between p-3 bg-background rounded-lg border border-border cursor-pointer">
                        <span className="text-foreground">Trade Exit Alerts</span>
                        <input
                            type="checkbox"
                            checked={config.alert_on_exit}
                            onChange={(e) => setConfig({ ...config, alert_on_exit: e.target.checked })}
                            className="w-4 h-4"
                        />
                    </label>

                    <label className="flex items-center justify-between p-3 bg-background rounded-lg border border-border cursor-pointer">
                        <span className="text-foreground">Error Alerts</span>
                        <input
                            type="checkbox"
                            checked={config.alert_on_errors}
                            onChange={(e) => setConfig({ ...config, alert_on_errors: e.target.checked })}
                            className="w-4 h-4"
                        />
                    </label>
                </div>
            </div>

            <div className="flex justify-end pt-6 border-t border-border">
                <button
                    onClick={saveConfig}
                    disabled={saving}
                    className="px-8 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-bold shadow-lg shadow-green-900/20"
                >
                    {saving ? (
                        <>Saving...</>
                    ) : (
                        <>
                            <Check className="h-5 w-5" />
                            Save Settings
                        </>
                    )}
                </button>
            </div>

            <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-start gap-2">
                    <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                    <div className="text-sm text-blue-800">
                        <p className="font-medium mb-1">Email Alert Features:</p>
                        <ul className="list-disc list-inside space-y-1">
                            <li>Instant notifications for every trade entry/exit</li>
                            <li>Clear Paper/Live mode tagging in subject and body</li>
                            <li>Formatted HTML emails with trade details and P&L</li>
                            <li>Secure Gmail App Password authentication</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
}
