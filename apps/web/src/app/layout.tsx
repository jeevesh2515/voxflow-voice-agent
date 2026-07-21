import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VoxFlow Voice Agent",
  description: "Voice operations, automated. Hindi + English supplier call agent.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
