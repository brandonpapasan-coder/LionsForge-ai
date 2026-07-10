import type { Metadata } from "next";
import "./globals.css";
import "./report-actions.css";
import "./evidence.css";
import "./education.css";
import "./workspace-links.css";
import "./module-progress.css";
import "./lesson.css";

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
