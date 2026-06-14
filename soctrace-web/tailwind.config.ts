import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        soc: {
          bg: "#08090D",
          surface: "#111219",
          panel: "#151723",
          panelAlt: "#1B1D2B",
          line: "rgba(255,255,255,0.08)",
          soft: "rgba(255,255,255,0.04)",
          text: "#F5F7FB",
          muted: "#9CA3B5",
          accent: "#4A6FA5",
          accentSoft: "#6B86B2",
          warm: "#F47C2A",
          warmSoft: "#C7865C"
        }
      },
      boxShadow: {
        panel: "0 22px 60px rgba(0, 0, 0, 0.32)",
        glow: "0 0 0 1px rgba(74,111,165,0.2), 0 18px 50px rgba(244,124,42,0.12)"
      },
      borderRadius: {
        xl2: "1.25rem"
      },
      fontFamily: {
        sans: ["Roboto", "ui-sans-serif", "system-ui", "sans-serif"]
      },
      backgroundImage: {
        "soc-grid":
          "linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px)",
        "soc-radial":
          "radial-gradient(circle at top left, rgba(74,111,165,0.16), transparent 24%), radial-gradient(circle at top right, rgba(244,124,42,0.1), transparent 18%)"
      }
    }
  },
  plugins: [],
} satisfies Config;
