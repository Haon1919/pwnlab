/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: '#0a0e1a',
          card: '#111827',
          border: '#1f2937',
          green: '#00ff88',
          red: '#ff3366',
          yellow: '#ffcc00',
          cyan: '#00d4ff',
          dim: '#4b5563',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      }
    },
  },
  plugins: [],
}
