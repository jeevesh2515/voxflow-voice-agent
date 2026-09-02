import type { Metadata } from "next";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import SmoothScroll from "@/components/SmoothScroll";
import AcousticBlackHoleCanvas from "@/components/AcousticBlackHoleCanvas";
import { ThemeProvider } from "@/lib/theme-context";
import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? "https://voxflow-voice-agent.vercel.app"
  ),
  title: "VoxFlow Voice Agent | Voice operations, automated",
  description:
    "VoxFlow Voice Agent handles Hindi-English business calls, captures POs and orders, checks stock and shipment status, and records every conversation.",
  openGraph: {
    type: "website",
    siteName: "VoxFlow Voice Agent",
    title: "VoxFlow Voice Agent | Voice operations, automated",
    description:
      "Autonomous voice agents for dispatch, customer service, and order capture. Sub-second response latency, fine-tuned English & Hindi models, and live 2-way database synchronization.",
    images: [
      {
        url: "/og-voxflow.jpg",
        width: 1200,
        height: 630,
        alt: "VoxFlow autonomous voice operations core",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "VoxFlow Voice Agent | Voice operations, automated",
    description:
      "Autonomous voice agents for dispatch, customer service, and order capture. Sub-200ms turn latency, English & Hindi, live database sync.",
    images: ["/og-voxflow.jpg"],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800;900&family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-[#030308] text-white font-sans antialiased flex flex-col selection:bg-[#5EEAD4] selection:text-[#030308] transition-colors duration-300">
        <ThemeProvider>
          <AuthProvider>
            <SmoothScroll />
            <AcousticBlackHoleCanvas />
            <Nav />
            <main className="flex-1 relative z-10">{children}</main>
            <Footer />
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
