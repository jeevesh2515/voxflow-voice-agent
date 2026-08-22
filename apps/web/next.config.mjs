/** @type {import('next').NextConfig} */
import path from "node:path";
import { fileURLToPath } from "node:url";

const appDir = path.dirname(fileURLToPath(import.meta.url));
const isVercelBuild = Boolean(process.env.VERCEL);
const defaultApiUrl = isVercelBuild ? "https://voxflow-voice-agent.onrender.com" : "http://localhost:8000";
const defaultWsUrl = isVercelBuild ? "wss://voxflow-voice-agent.onrender.com" : "ws://localhost:8000";
const apiUrl = process.env.NEXT_PUBLIC_API_URL || defaultApiUrl;
const wsUrl = process.env.NEXT_PUBLIC_WS_URL || defaultWsUrl;

const nextConfig = {
  turbopack: {
    root: appDir,
  },
  // Vercel supplies its own trace packaging and skips standalone. The Docker
  // build runs from the apps/web context ALONE, so the standalone tracing root
  // MUST be the app dir — a root above it makes Next nest server.js under a
  // subpath and the runner can't find /app/server.js.
  ...(process.env.VERCEL ? {} : { output: "standalone", outputFileTracingRoot: appDir }),
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
