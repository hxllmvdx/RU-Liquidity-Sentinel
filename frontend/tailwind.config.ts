import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#f5f8fc",
        surface: "#ffffff",
        border: "#d5e1ef",
        ink: "#111111",
        muted: "#3f4b5c",
        primary: "#1459b8",
        "primary-soft": "#dce9fb",
        accent: "#ea7b22",
        success: "#2e8b57",
        caution: "#d8a229",
        danger: "#cc4b37"
      },
      boxShadow: {
        panel: "0 12px 32px rgba(20, 89, 184, 0.08)"
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.5rem"
      }
    }
  },
  plugins: []
};

export default config;
