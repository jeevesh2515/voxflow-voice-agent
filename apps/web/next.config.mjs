import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const appDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(appDir, "../..");
const turbopackRoot = fs.existsSync(path.join(appDir, "node_modules", "next")) ? appDir : repoRoot;

const isVercelBuild = Boolean(process.env.VERCEL);
const defaultApiUrl = isVercelBuild ? "https://voxflow-voice-agent.onrender.com" : "http://localhost:8000";
const defaultWsUrl = isVercelBuild ? "wss://voxflow-voice-agent.onrender.com" : "ws://localhost:8000";
const apiUrl = process.env.NEXT_PUBLIC_API_URL || defaultApiUrl;
const wsUrl = process.env.NEXT_PUBLIC_WS_URL || defaultWsUrl;

const nextConfig = {
  turbopack: {
    root: turbopackRoot,
  },
  // Vercel supplies its own trace packaging and skips standalone.
  ...(process.env.VERCEL ? {} : { output: "standalone", outputFileTracingRoot: turbopackRoot }),
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
