import "./globals.css";
import Sidebar from "@/components/Sidebar";
import { MarketProvider } from "@/context/MarketContext";
import { MarketStatus } from "@/components/MarketStatus"; // We will create this next

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-background text-foreground antialiased min-h-screen flex">
        <MarketProvider>
          {/* Sidebar Navigation */}
          <Sidebar />

          {/* Main Content Area */}
          <main className="flex-1 flex flex-col h-screen overflow-hidden">
            {/* Simple Header for Connection Status */}
            <MarketStatus />

            {/* Page Content */}
            <div className="flex-1 overflow-auto p-6">
              {children}
            </div>
          </main>
        </MarketProvider>
      </body>
    </html>
  );
}
