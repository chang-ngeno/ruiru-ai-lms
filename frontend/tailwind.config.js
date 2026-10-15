/** Theme taken from the "AI Training for Everyone" poster:
 *  deep navy panels, highlighter-yellow brush strokes, green / blue / purple path colours,
 *  bold rounded headings with a handwritten accent font. */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: "#0B2A6F", 700: "#123C9C", 800: "#0B2A6F", 900: "#071A47", 950: "#050F2B" },
        brand: { DEFAULT: "#F5D90A", 600: "#E0C500" },
        panel: "#EEF3FF",
        path: { beginner: "#1B8A3A", intermediate: "#2F6FDE", advanced: "#7B3FC4" },
      },
      fontFamily: {
        display: ["Poppins", "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        script: ["Caveat", "cursive"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: { glow: "0 10px 40px -10px rgba(245,217,10,.45)" },
    },
  },
  plugins: [],
};
