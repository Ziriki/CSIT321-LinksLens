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
        background: "#ffffff",
        foreground: "#171717",

        card: "#ffffff",
        "card-foreground": "#171717",

        primary: "#2563eb",
        "primary-foreground": "#ffffff",

        secondary: "#f3f4f6",
        "secondary-foreground": "#171717",

        muted: "#f3f4f6",
        "muted-foreground": "#6b7280",

        border: "#e5e7eb",
        input: "#e5e7eb",

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