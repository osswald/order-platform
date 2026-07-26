import { resolve } from 'node:path'
import { defineConfig } from 'vite'

export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        ablauf: resolve(__dirname, 'ablauf/index.html'),
        funktionen: resolve(__dirname, 'funktionen/index.html'),
        kontakt: resolve(__dirname, 'kontakt/index.html'),
        datenschutz: resolve(__dirname, 'datenschutz/index.html'),
      },
    },
  },
})
