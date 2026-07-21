import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "surface-variant": "#1e1e30",
        "outline-variant": "#302840",
        "surface-container-low": "#111118",
        "surface-bright": "#1a1a2e",
        "surface-container-highest": "#28283e",
        "surface-container-high": "#28283e",
        "outline": "#5a5068",
        "surface-dim": "#0f0f1a",
        "background": "#0a0a12",
        "primary": "#ff2d78",
        "on-error-container": "#ffa0a0",
        "tertiary": "#ffe04a",
        "on-primary": "#1a0010",
        "surface": "#0f0f1a",
        "surface-container": "#141422",
        "on-surface-variant": "#a098b0",
        "on-surface": "#e8e0f0",
        "inverse-surface": "#e8e0f0",
        "surface-container-lowest": "#0a0a12",
        "error": "#ff4444",
        "secondary": "#00ffcc",
        "on-tertiary": "#1a1000",

        foreground: "#e8e0f0",
        muted: {
          DEFAULT: "#1e1e30",
          foreground: "#a098b0",
        },
        border: "#302840",
        card: {
          DEFAULT: "#0f0f1a",
          foreground: "#e8e0f0",
        },
        accent: {
          DEFAULT: "#1e1e30",
          foreground: "#e8e0f0",
        },
        success: { 500: "#00ffcc" },
        warn: { 500: "#ffe04a" },
        danger: { 500: "#ff4444" },
      },
      fontFamily: {
        headline: ["Sora", "sans-serif"],
        display: ["Sora", "sans-serif"],
        body: ["Inter", "sans-serif"],
        label: ["Space Grotesk", "monospace"],
        sans: ["Inter", "sans-serif"],
        mono: ["Space Grotesk", "monospace"],
      },
      borderRadius: {
        DEFAULT: "0.125rem",
        lg: "0.25rem",
        xl: "0.5rem",
        "2xl": "1rem",
        "3xl": "1.5rem",
      },
      boxShadow: {
        glow: "0 0 20px rgba(255,45,120,0.4), inset 0 0 12px rgba(255,45,120,0.1)",
      },
    },
  },
  plugins: [],
};
export default config;
