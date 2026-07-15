"use client";

import React, { createContext, useContext, ReactNode, useState, useEffect } from "react";
import { useSocket } from "@/hooks/useSocket";
import { Socket } from "socket.io-client";

interface MarketData {
    [token: string]: {
        ltp: number;
        change: number;
        percentChange: number;
    }
}

interface MarketContextType {
    socket: Socket | null;
    isConnected: boolean;
    marketData: MarketData;
}

const MarketContext = createContext<MarketContextType>({
    socket: null,
    isConnected: false,
    marketData: {},
});

export const useMarket = () => useContext(MarketContext);

export const MarketProvider = ({ children }: { children: ReactNode }) => {
    const { socket, isConnected } = useSocket();
    const [marketData, setMarketData] = useState<MarketData>({});

    useEffect(() => {
        if (!socket) return;

        socket.on("market_data", (data: any) => {
            // Angel One V2 structure: { token: "...", last_traded_price: 12300, ... }
            // We need to parse this.
            // Example message from manual feed:
            // {'token': '99926000', 'last_traded_price': 25950.0, ...}

            if (data && data.token) {
                setMarketData(prev => ({
                    ...prev,
                    [data.token]: {
                        ltp: data.last_traded_price || 0,
                        change: 0, // Need to calc from close provided in data
                        percentChange: 0
                    }
                }));
            }
        });

        return () => {
            socket.off("market_data");
        };
    }, [socket]);

    return (
        <MarketContext.Provider value={{ socket, isConnected, marketData }}>
            {children}
        </MarketContext.Provider>
    );
};
