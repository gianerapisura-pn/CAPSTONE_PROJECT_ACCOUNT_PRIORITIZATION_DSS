import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "PESLC Account Prioritization DSS",
  description: "Decision support for account prioritization based on historical sales and collection records."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <aside className="sidebar">
            <strong>PESLC DSS</strong>
            <nav aria-label="Primary navigation">
              <Link href="/">Dashboard</Link>
              <Link href="/import">Import</Link>
              <Link href="/accounts">Account Ranking</Link>
              <Link href="/analytics">Analytics</Link>
              <Link href="/reports">Reports</Link>
            </nav>
          </aside>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
