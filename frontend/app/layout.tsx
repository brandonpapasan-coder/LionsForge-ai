import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Onyxmane Intelligence",
  description: "Evidence-based research, education, and AI mentorship.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
