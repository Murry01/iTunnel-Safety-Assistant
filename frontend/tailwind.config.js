/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Base surfaces (cool graphite scale). Values come from CSS custom
        // properties (see src/index.css) so the whole app repaints when the
        // `.light` class toggles on <html> — nothing here needs to change
        // per theme, only the variable definitions do.
        ink: {
          950: "var(--ink-950)", // sidebar / panels
          900: "var(--ink-900)", // app background
          850: "var(--ink-850)", // trace card
          800: "var(--ink-800)", // composer, chips
          750: "var(--ink-750)", // menus
          700: "var(--ink-700)", // hover
          650: "var(--ink-650)", // menu hover
          600: "var(--ink-600)", // borders
          500: "var(--ink-500)", // strong borders
          400: "var(--ink-400)", // scrollbar
        },
        // Text (fog scale)
        fog: {
          50: "var(--fog-50)",
          100: "var(--fog-100)",
          200: "var(--fog-200)",
          300: "var(--fog-300)",
          350: "var(--fog-350)",
          400: "var(--fog-400)",
          500: "var(--fog-500)",
          600: "var(--fog-600)",
          700: "var(--fog-700)",
          800: "var(--fog-800)",
        },
        // Brand cyan
        accent: {
          DEFAULT: "var(--accent-color)",
          bright: "var(--accent-bright)",
          deep: "var(--accent-deep)",
          wash: "var(--accent-wash)",
          washHover: "var(--accent-washHover)",
          bubble: "var(--accent-bubble)",
          tagText: "var(--accent-tagText)",
          tagBg: "var(--accent-tagBg)",
        },
        // Risk amber
        risk: {
          text: "var(--risk-text)",
          icon: "var(--risk-icon)",
          bg: "var(--risk-bg)",
          dot: "var(--risk-dot)",
        },
        danger: "var(--danger-color)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      keyframes: {
        pulseDot: {
          "0%, 80%, 100%": { opacity: "0.3" },
          "40%": { opacity: "1" },
        },
        fadeUp: {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        pulseDot: "pulseDot 1.2s infinite",
        fadeUp: "fadeUp 0.25s ease-out",
      },
    },
  },
  plugins: [],
};
