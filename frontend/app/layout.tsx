import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { CallProvider } from "@/lib/call-context";
import Header from "@/components/Header";
import CallOverlay from "@/components/CallOverlay";
import { Analytics } from "@vercel/analytics/react";

export const metadata: Metadata = {
  title: "Bridge Point — Micro-Employment Platform",
  description:
    "Connect with skilled micro-workers in your city. Post jobs, find work, and get things done — instantly.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#0071e3" />
        <link rel="apple-touch-icon" href="/icon-192.png" />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                  navigator.serviceWorker.register('/sw.js', { scope: '/' });
                });
              }
            `,
          }}
        />
      </head>
      <body className="min-h-screen bg-[var(--color-bp-white)]" style={{ fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif" }}>
        <AuthProvider>
          <CallProvider>
            <Header />
            <main>{children}</main>
            <CallOverlay />
          </CallProvider>
        </AuthProvider>
        <Analytics />
      </body>
    </html>
  );
}
