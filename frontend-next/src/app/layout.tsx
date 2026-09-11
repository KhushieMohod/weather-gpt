import './globals.css';
import type { Metadata } from 'next';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';

export const metadata: Metadata = {
  title: 'WeatherGPT | Multi-Source Disaster Weather Intelligence',
  description:
    'Unified disaster weather intelligence integrating IMD, MOSDAC, GFS/WRF, ERA5 — SIH 2026 Problem 26068.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Header />
        <div className="app-container">
          <Sidebar />
          {children}
        </div>
        <footer className="footer">
          <span>WeatherGPT | SIH 2026 | Problem Statement 26068</span>
          <span>
            Data from: IMD | MOSDAC/ISRO | GFS | ERA5 | NDMA/SACHET | CWC
          </span>
          <span>Data status and timestamps shown transparently.</span>
        </footer>
      </body>
    </html>
  );
}
