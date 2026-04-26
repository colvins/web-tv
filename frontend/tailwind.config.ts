import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      colors: {
        cinema: {
          950: '#050507',
          900: '#0b0c10',
          800: '#14161d',
          700: '#20232d',
          500: '#51596b',
        },
        aurora: '#89b4ff',
        ember: '#ffb86b',
      },
      boxShadow: {
        glow: '0 24px 80px rgba(137, 180, 255, 0.18)',
      },
    },
  },
  plugins: [],
} satisfies Config
