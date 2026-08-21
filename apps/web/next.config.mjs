/** @type {import('next').NextConfig} */
import path from "node:path";
import { fileURLToPath } from "node:url";

const monorepoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const isVercelBuild = Boolean(process.env.VERCEL);
const defaultApiUrl = isVercelBuild ? "https://voxflow-voice-agent.fly.dev" : "http://localhost:8000";
const defaultWsUrl = isVercelBuild ? "wss://voxflow-voice-agent.fly.dev" : "ws://localhost:8000";
const apiUrl = process.env.NEXT_PUBLIC_API_URL || defaultApiUrl;
const wsUrl = process.env.NEXT_PUBLIC_WS_URL || defaultWsUrl;

const nextConfig = {
  turbopack: {
    root: monorepoRoot,
  },
  // Vercel supplies its own trace packaging; the Docker build still needs standalone output.
  ...(process.env.VERCEL ? {} : { output: "standalone" }),
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: apiUrl,
    NEXT_PUBLIC_WS_URL: wsUrl,
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${apiUrl}/api/:path*` },
    ];
  },
};

export default nextConfig;
