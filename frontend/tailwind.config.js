/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bgPrimary: '#F7F9FA',
        colorPrimary: {
          DEFAULT: '#1F5B8C',
          hover: '#184870',
          light: '#EBF3FA',
        },
        colorAccent: {
          DEFAULT: '#E8A33D',
          hover: '#CF8E2C',
          light: '#FEF8EE',
        },
        colorCritical: {
          DEFAULT: '#C1444B', // Reserved strictly for SUSPICIOUS / critical warnings
          light: '#FCEFEF',
        },
        colorVerified: {
          DEFAULT: '#2E8B57',
          hover: '#257247',
          light: '#EEF7F2',
        },
        textPrimary: '#202325',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        subtle: '0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)',
        card: '0 4px 6px -1px rgba(31, 91, 140, 0.06), 0 2px 4px -2px rgba(31, 91, 140, 0.06)',
        elevated: '0 10px 15px -3px rgba(31, 91, 140, 0.08), 0 4px 6px -4px rgba(31, 91, 140, 0.05)',
      }
    },
  },
  plugins: [],
}
