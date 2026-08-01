/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#FFFFFF",
          secondary: "#F8FAFC",
        },
        card: "#FFFFFF",
        border: "#E5E7EB",
        ink: {
          DEFAULT: "#111827",
          secondary: "#6B7280",
        },
        accent: {
          DEFAULT: "#0F766E",
          50: "#F0FDFA",
          100: "#CCFBF1",
          200: "#99F6E4",
          600: "#0D9488",
          700: "#0F766E",
          800: "#115E59",
        },
        success: "#16A34A",
        warning: "#F59E0B",
        danger: "#DC2626",
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        display: ["Manrope", "Inter", "sans-serif"],
        mono: [
          "IBM Plex Mono",
          "ui-monospace",
          "SFMono-Regular",
          "monospace",
        ],
      },
      borderRadius: {
        card: "16px",
        control: "12px",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(17, 24, 39, 0.04), 0 4px 12px rgba(17, 24, 39, 0.04)",
        softLg:
          "0 2px 4px rgba(17, 24, 39, 0.04), 0 12px 32px rgba(17, 24, 39, 0.06)",
      },
      keyframes: {
        scanline: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
        pulseSoft: {
          "0%, 100%": { transform: "scale(1)", opacity: "0.85" },
          "50%": { transform: "scale(1.03)", opacity: "1" },
        },
        markerPulse: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(15,118,110,0.35)" },
          "50%": { boxShadow: "0 0 0 6px rgba(15,118,110,0)" },
        },
      },
      animation: {
        scanline: "scanline 1.5s linear infinite",
        pulseSoft: "pulseSoft 1.2s ease-in-out infinite",
        markerPulse: "markerPulse 0.9s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
