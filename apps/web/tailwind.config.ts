import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f5f6f8",
          100: "#e6e8ed",
          200: "#c4c8d3",
          300: "#9aa1b0",
          400: "#6f7689",
          500: "#4a5165",
          600: "#2f3548",
          700: "#1f2433",
          800: "#141826",
          900: "#0b0e1a",
          950: "#06080f",
        },
        vox: {
          50: "#eaf3ff",
          100: "#d4e6ff",
          200: "#a8cdff",
          300: "#7cb4ff",
          400: "#509bff",
          500: "#2682ff",
          600: "#0d68e0",
          700: "#0950b3",
          800: "#063a86",
          900: "#03245a",
        },
        success: { 500: "#10b981" },
        warn:    { 500: "#f59e0b" },
        danger:  { 500: "#ef4444" },
      },
      fontFamily: {
        sans: ["var(--font-satoshi)", "system-ui", "sans-serif"],
        mono: ["var(--font-space-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(38,130,255,0.4), 0 8px 32px rgba(38,130,255,0.15)",
      },
    },
  },
  plugins: [],
};
export default config;
