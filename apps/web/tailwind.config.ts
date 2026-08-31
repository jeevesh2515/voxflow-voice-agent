import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        obsidian: "#07070e",
        "obsidian-light": "#0f0f1c",
        "surface-variant": "#1e1e30",
        "outline-variant": "#302840",
        "surface-container-low": "#111118",
        "surface-bright": "#1a1a2e",
        "surface-container-highest": "#28283e",
        "surface-container-high": "#28283e",
        "outline": "#5a5068",
        "surface-dim": "#0f0f1a",
        "background": "#07070e",
        "primary": "#ff2d78",
        "on-error-container": "#ffa0a0",
        "tertiary": "#ffe04a",
        "on-primary": "#1a0010",
        "surface": "#0f0f1c",
        "surface-container": "#141422",
        "on-surface-variant": "#94a3b8",
        "on-surface": "#f8fafc",
        "inverse-surface": "#f8fafc",
        "surface-container-lowest": "#07070e",
        "error": "#ff4444",
        "secondary": "#00ffcc",
        "on-tertiary": "#1a1000",

        foreground: "#f8fafc",
        muted: {
          DEFAULT: "#1e1e30",
          foreground: "#94a3b8",
        },
        border: "rgba(255,255,255,0.07)",
        card: {
          DEFAULT: "rgba(15,15,28,0.8)",
          foreground: "#f8fafc",
        },
        accent: {
          DEFAULT: "#1e1e30",
          foreground: "#f8fafc",
        },
        success: { 400: "#00ffcc", 500: "#00ffcc" },
        warn: { 400: "#f59e0b", 500: "#f59e0b" },
        danger: { 400: "#ef4444", 500: "#ff4444" },
      },
      fontFamily: {
        headline: ["Sora", "sans-serif"],
        display: ["Sora", "sans-serif"],
        body: ["Inter", "sans-serif"],
        label: ["JetBrains Mono", "Geist Mono", "monospace"],
        sans: ["Inter", "Geist", "Plus Jakarta Sans", "sans-serif"],
        mono: ["JetBrains Mono", "Geist Mono", "monospace"],
      },
      borderRadius: {
        DEFAULT: "0.125rem",
        lg: "0.25rem",
        xl: "0.5rem",
        "2xl": "1rem",
        "3xl": "1.5rem",
      },
      boxShadow: {
        glow: "0 0 25px rgba(255,45,120,0.35)",
        "glow-cyan": "0 0 20px rgba(0,255,204,0.25)",
        "glow-amber": "0 0 20px rgba(245,158,11,0.25)",
      },
    },
  },
  plugins: [],
};
export default config;
