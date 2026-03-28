/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,jsx,ts,tsx}',
    './components/**/*.{js,jsx,ts,tsx}'
  ],
  darkMode: 'class',
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",

        card: "var(--card)",
        "card-foreground": "var(--card-foreground)",

        // primary stays hardcoded so bg-primary/10 opacity modifiers work
        primary: "#2563eb",
        "primary-foreground": "#ffffff",

        secondary: "var(--secondary)",
        "secondary-foreground": "var(--secondary-foreground)",

        muted: "var(--muted)",
        "muted-foreground": "var(--muted-foreground)",

        border: "var(--border)",
        input: "var(--input)",

        safe: "#22c55e",
        suspicious: "#f59e0b",
        malicious: "#ef4444"
      },

      borderRadius: {
        sm: "8px",
        md: "12px",
        lg: "16px",
        xl: "20px"
      }
    },
  },
  plugins: [],
};