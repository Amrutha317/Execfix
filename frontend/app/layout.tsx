import "./globals.css";
import type { ReactNode } from "react";
import { Inter, JetBrains_Mono } from "next/font/google";
import TopNav from "@/components/top-nav";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-code",
  weight: ["400", "500", "600"]
});

export const metadata = {
  title: "Autonomous Code Debugger",
  description: "Next.js 16 frontend for Python debugging agent"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body>
        <div className="shell">
          <header className="topbar">
            <div className="topbar__brand">
              <div className="brand__title">Autonomous Code Debugger</div>
            </div>
            <div className="topbar__center">
              <TopNav />
            </div>
            <div className="topbar__right" id="topbar-actions" />
          </header>
          <div className="page">{children}</div>
        </div>
      </body>
    </html>
  );
}
