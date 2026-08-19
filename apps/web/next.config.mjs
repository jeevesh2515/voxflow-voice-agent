/** @type {import('next').NextConfig} */
import path from "node:path";
import { fileURLToPath } from "node:url";

const monorepoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

const nextConfig = {
  turbopack: {
    root: monorepoRoot,
  },
  // Vercel supplies its own trace packaging; the Docker build still needs standalone output.
  ...(process.env.VERCEL ? {} : { output: "standalone" }),
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000",
  },
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      { source: "/api/:path*", destination: `${apiUrl}/api/:path*` },
    ];
  },
};

export default nextConfig;
