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

        /**
         * Field system — the data-instrument visual world for Operate
         * surfaces (dashboard, deep-dive, calibration, workspace, review
         * queue). Deliberately monochrome: black ground, white/grey type
         * and rules, one reserved accent (field.alert) used only for
         * unmet/error/critical states, always paired with a text label so
         * color is never the sole signal. Coexists with the tokens above —
         * pages using the incumbent "civic paper" world are unaffected
         * until they are individually migrated.
         */
        field: {
          bg: "#050505",
          "bg-raised": "#0D0D0D",
          rule: "#2A2A2A",
          "rule-strong": "#454545",
          fg: "#F2F2F0",
          "fg-muted": "#9A9A96",
          "fg-subtle": "#5C5C58",
          alert: "#FF3B30",
          "alert-bg": "#1A0705",
          "alert-border": "#4D1310",
        },

        /**
         * Terminal system — the green-phosphor CRT visual world for the
         * landing page (the one Persuade surface in this product).
         * Committed color strategy: phosphor green is not an accent, it is
         * the page's entire material, carrying body text, rules, glow and
         * motion alike. Distinct from the field system's black/white
         * Operate world on purpose — the landing page is allowed the
         * warmth and "wow" a working screen should never have.
         */
        terminal: {
          bg: "#050806",
          fg: "#33FF66",
          dim: "#0DB050",
          faint: "#076A33",
          shadow: "#03301A",
          bloom: "#A7FFC2",
          cursor: "#66FFA3",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Georgia", "serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
        field: ["var(--font-field)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 2px rgb(23 34 51 / 0.05), 0 12px 32px rgb(23 34 51 / 0.06)",
        lift: "0 2px 4px rgb(23 34 51 / 0.06), 0 18px 45px rgb(23 34 51 / 0.10)",
      },
      // One radius system for the whole product: 6px is the only corner
      // rounding value anything is allowed to use. Sharp everywhere else —
      // rules and hairlines carry structure instead of rounded containers.
      borderRadius: {
        DEFAULT: "6px",
        none: "0px",
        full: "9999px",
        lg: "6px",
        xl: "6px",
        "2xl": "6px",
      },
      // Asymmetric layout primitives — deliberately uneven column ratios so
      // sections don't default to 50/50 or 3-up grids.
      gridTemplateColumns: {
        "editorial-a": "minmax(0, 1.6fr) minmax(0, 1fr)",
        "editorial-b": "minmax(0, 1fr) minmax(0, 1.9fr)",
        "editorial-c": "0.9fr 1.4fr 0.7fr",
      },
      letterSpacing: {
        tightest: "-0.045em",
      },
    },
  },
  plugins: [],
};

export default config;
