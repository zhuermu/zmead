import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { AuthProvider } from "@/components/auth";
import { CookieConsent } from "@/components/gdpr";
import { ErrorBoundary } from "@/components/error";
import { ToastContainer } from "@/components/toast";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "AAE Web Platform",
  description: "Automated Ad Engine - AI-powered advertising platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ErrorBoundary>
          <AuthProvider>
            {children}
          </AuthProvider>
          <CookieConsent />
          <ToastContainer />
        </ErrorBoundary>
      </body>
    </html>
  );
}
