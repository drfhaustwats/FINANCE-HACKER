/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {},
  },
  safelist: [
    'grid-cols-1',
    'lg:grid-cols-2',
    'gap-6',
    'items-start',
    'grid-cols-1',
    'gap-6',
    'grid-cols-1',
    'lg:grid-cols-3',
    'gap-4',
    'items-start',
    'grid-cols-1',
    'md:grid-cols-2',
    'xl:grid-cols-4',
    'gap-4',
    'items-start'
  ],
  plugins: [],
};