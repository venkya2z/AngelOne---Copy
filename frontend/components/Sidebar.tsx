"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Wallet, Briefcase, Activity, Settings, TrendingUp, Mail, Beaker } from "lucide-react";
import clsx from "clsx";

const menuItems = [
    { name: "Dashboard", path: "/", icon: LayoutDashboard },
    { name: "Positions (Live)", path: "/positions", icon: TrendingUp },
    { name: "Paper Simulation", path: "/paper", icon: Beaker },
    { name: "Funds", path: "/funds", icon: Wallet },
    { name: "Settings", path: "/settings", icon: Settings },
    { name: "Email Alerts", path: "/email-alerts", icon: Mail },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <div className="h-screen w-64 bg-card border-r border-border flex flex-col p-4">
            {/* Brand */}
            <div className="flex items-center gap-2 mb-8 px-2">
                <Activity className="text-primary h-8 w-8" />
                <h1 className="font-bold text-xl tracking-tight">Angel Bot <span className="text-primary">Pro</span></h1>
            </div>

            {/* Menu */}
            <nav className="flex-1 space-y-2">
                {menuItems.map((item) => {
                    const isActive = pathname === item.path;
                    return (
                        <Link
                            key={item.name}
                            href={item.path}
                            className={clsx(
                                "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all font-medium",
                                isActive
                                    ? "bg-primary text-primary-foreground shadow-sm"
                                    : "text-foreground/80 hover:bg-secondary/10 hover:text-foreground"
                            )}
                        >
                            <item.icon className="h-5 w-5" />
                            <span>{item.name}</span>
                        </Link>
                    );
                })}
            </nav>

            {/* Connection Status Footnote */}
            <div className="mt-auto px-2">
                <div className="bg-secondary/10 rounded-lg p-3 text-xs text-secondary-foreground font-medium">
                    v2.0 • FMSI-Elastic
                </div>
            </div>
        </div>
    );
}
