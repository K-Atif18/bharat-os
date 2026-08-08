import type { Metadata } from "next";

import { AppShell } from "@/components/AppShell";
import "@/app/globals.css";

export const metadata: Metadata = {
  title: "Bharat OS — Government funding execution",
  description:
    "Evidence-backed eligibility reasoning, document guidance and application drafting for Indian government funding schemes.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
