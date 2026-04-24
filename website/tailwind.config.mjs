import typography from '@tailwindcss/typography';

export default {
  content: ['./src/**/*.{astro,html,js}'],
  theme: {
    extend: {
      colors: {
        brand: {
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          900: '#1e1b4b',
        },
      },
    },
  },
  plugins: [typography],
};
