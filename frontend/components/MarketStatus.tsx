"use client";

import { useMarket } from "@/context/MarketContext";
import { Badge } from "lucide-react";
import { motion } from "framer-motion";
import { useState, useEffect } from "react";

export function MarketStatus() {
    const { isConnected } = useMarket();
    const [currentTime, setCurrentTime] = useState("");

    // Client-side only time rendering to avoid hydration errors
    useEffect(() => {
        setCurrentTime(new Date().toLocaleTimeString());
        const timer = setInterval(() => {
            setCurrentTime(new Date().toLocaleTimeString());
        }, 1000);
        return () => clearInterval(timer);
    }, []);

    return (
        <div className="flex items-center justify-between py-4 border-b border-border bg-card/50 px-6 backdrop-blur-sm sticky top-0 z-10">
            <div className="flex items-center gap-4">
                {/* Connection Indicator */}
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-secondary/20 border border-border">
                    <motion.div
                        animate={{ opacity: isConnected ? [1, 0.5, 1] : 1 }}
                        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                        className={`w-2 h-2 rounded-full ${isConnected ? "bg-success shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-danger"}`}
                    />
                    <span className={`text-xs font-medium ${isConnected ? "text-success" : "text-danger"}`}>
                        {isConnected ? "System Online" : "Disconnected"}
                    </span>
                </div>
            </div>

            {/* Right Side - Time */}
            <div className="text-xs text-foreground/70 font-mono font-medium">
                {currentTime || "--:--:--"}
            </div>
        </div>
    );
}
