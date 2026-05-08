import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        sand: "#f8fafc",
        accent: "#0f766e",
        alert: "#b91c1c",
        warning: "#b45309"
      }
    }
  },
  plugins: []
};

export default config;
