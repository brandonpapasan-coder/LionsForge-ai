import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LionsForge AI",
  description: "Evidence-based investment research and education intelligence.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
