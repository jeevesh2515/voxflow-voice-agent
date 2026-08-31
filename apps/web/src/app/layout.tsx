import type { Metadata } from "next";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import { ThemeProvider } from "@/lib/theme-context";
import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

export const metadata: Metadata = {
  // Required for og:image / twitter:image to serialise as absolute URLs.
  // Without it Next falls back to http://localhost:3000 and the share card
  // silently 404s in production.
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
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap"
          rel="stylesheet"
        />
        {/* The hero hides its copy until JS marks the stage ready, so the opening
            frame is a clean visual. Without JS that class never lands, which would
            leave the headline permanently invisible to crawlers and no-JS clients. */}
        <noscript
          dangerouslySetInnerHTML={{
            __html: `<style>.hero-stage .hero-copy,.hero-stage .hero-console{opacity:1!important;transform:none!important}</style>`,
          }}
        />
      </head>
      <body className="min-h-screen bg-[#0a0a12] text-[#e8e0f0] font-sans antialiased flex flex-col selection:bg-[#ff2d78] selection:text-[#1a0010] transition-colors duration-300">
        <ThemeProvider>
          <AuthProvider>
            <Nav />
            <main className="flex-1">{children}</main>
            <Footer />
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
