import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  output: 'static',
  site: 'https://GenAI-Gurus.github.io',
  base: '/signal-archive',
  integrations: [tailwind()],
});
