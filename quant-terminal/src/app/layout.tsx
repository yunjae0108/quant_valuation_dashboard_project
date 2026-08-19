import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";

// Industry standard Next.js font optimization
const outfit = Outfit({ 
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Quant Engine | Advanced Terminal",
  description: "Enterprise-grade quantitative valuation dashboard built with Next.js",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${outfit.className} antialiased`}>
        {children}
      </body>
    </html>
  );
}