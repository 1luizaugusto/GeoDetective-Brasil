import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// base relativa: funciona no GitHub Pages (subpasta /<repo>/) e em qualquer hospedagem estática
export default defineConfig({
  base: "./",
  plugins: [svelte()],
});
