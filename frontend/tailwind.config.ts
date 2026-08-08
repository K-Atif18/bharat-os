import type { Config } from "tailwindcss";

/**
 * Bharat OS visual language: calm civic intelligence.
 *
 * Warm paper surfaces and institutional ink carry the interface; rust is kept
 * for actions, while green/amber/red remain reserved for evidence states.
 * Every foreground/background pair here is chosen for WCAG AA contrast.
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#172233",
          muted: "#4B5563",
          subtle: "#687386",
          inverse: "#FBF8F1",
        },
        surface: {
          DEFAULT: "#FFFEFB",
          canvas: "#F4F0E7",
          sunken: "#ECE7DC",
          raised: "#FFFFFF",
          border: "#D9D1C4",
          strong: "#B8AD9D",
        },
        brand: {
          DEFAULT: "#9A3412",
          hover: "#7C2D12",
          subtle: "#FFF4E8",
          border: "#F5B67B",
        },
        civic: {
          navy: "#16243A",
          blue: "#284B7A",
          saffron: "#D5672A",
          green: "#176246",
        },
        met: {
          fg: "#176246",
          bg: "#EAF7F0",
          border: "#A7D7BC",
        },
        unmet: {
          fg: "#9F2929",
          bg: "#FFF0EE",
          border: "#E8B5AF",
        },
        unverified: {
          fg: "#744A06",
          bg: "#FFF8E2",
          border: "#E4CE8C",
        },
        info: {
          fg: "#26466F",
          bg: "#EDF4FC",
          border: "#B8CEE8",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Georgia", "serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 2px rgb(23 34 51 / 0.05), 0 12px 32px rgb(23 34 51 / 0.06)",
        lift: "0 2px 4px rgb(23 34 51 / 0.06), 0 18px 45px rgb(23 34 51 / 0.10)",
      },
    },
  },
  plugins: [],
};

export default config;
