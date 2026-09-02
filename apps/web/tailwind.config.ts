import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#030308",
        background: "#030308",
        foreground: "#ffffff",
        accent: {
          DEFAULT: "#5EEAD4",
          foreground: "#030308",
        },
        primary: "#5EEAD4",
        "on-primary": "#030308",
        secondary: "#5EEAD4",
        "surface-variant": "#11111a",
        "outline-variant": "#222233",
        "surface-container-low": "#0a0a10",
        "surface-bright": "#161622",
        "surface-container-highest": "#1c1c2b",
        "surface-container-high": "#181826",
        "outline": "#4a455a",
        "surface-dim": "#08080e",
        "on-error-container": "#ffa0a0",
        "tertiary": "#ffe04a",
        "surface": "#0a0a12",
        "surface-container": "#0e0e18",
        "on-surface-variant": "#a098b0",
        "on-surface": "#ffffff",
        "inverse-surface": "#ffffff",
        "surface-container-lowest": "#030308",
        "error": "#ff4444",
        "on-tertiary": "#1a1000",

        muted: {
          DEFAULT: "#11111a",
          foreground: "#a098b0",
        },
        border: "#222233",
        card: {
          DEFAULT: "#08080e",
          foreground: "#ffffff",
        },
        success: { 500: "#5EEAD4" },
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
        glow: "0 0 20px rgba(94,234,212,0.4), inset 0 0 12px rgba(94,234,212,0.1)",
      },
    },
  },
  plugins: [],
};
export default config;
