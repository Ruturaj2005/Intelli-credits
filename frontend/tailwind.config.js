/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#020608',
        surface: '#0a0f12',
        surface2: '#111820',
        'border-col': '#1a2530',
        accent: '#00d4aa',
        accent2: '#0099ff',
        danger: '#ef476f',
        warning: '#ffd166',
        'text-primary': '#e8f0f5',
        muted: '#4a6070',
      },
      fontFamily: {
        syne: ['Syne', 'sans-serif'],
        mono: ['"DM Mono"', 'monospace'],
        sans: ['Inter', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '8px',
        lg: '12px',
      },
      boxShadow: {
        accent: '0 0 20px rgba(0, 212, 170, 0.08)',
        'accent-md': '0 0 30px rgba(0, 212, 170, 0.15)',
        danger: '0 0 20px rgba(239, 71, 111, 0.1)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.4s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
