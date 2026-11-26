<script lang="ts">
  // bandeirinhas em SVG (emoji de bandeira não aparece no Windows)
  let { lang }: { lang: "pt" | "en" } = $props();
</script>

{#if lang === "pt"}
  <svg class="flag" viewBox="0 0 20 14" aria-hidden="true">
    <rect width="20" height="14" fill="#009c3b" />
    <polygon points="10,1.6 18.2,7 10,12.4 1.8,7" fill="#ffdf00" />
    <circle cx="10" cy="7" r="3.3" fill="#002776" />
  </svg>
{:else}
  <svg class="flag" viewBox="0 0 20 14" aria-hidden="true">
    <rect width="20" height="14" fill="#012169" />
    <path d="M0,0 L20,14 M20,0 L0,14" stroke="#fff" stroke-width="2.8" />
    <path d="M0,0 L20,14 M20,0 L0,14" stroke="#c8102e" stroke-width="1.2" />
    <path d="M10,0 V14 M0,7 H20" stroke="#fff" stroke-width="4.2" />
    <path d="M10,0 V14 M0,7 H20" stroke="#c8102e" stroke-width="2.4" />
  </svg>
{/if}

<style>
  .flag { width: 20px; height: 14px; flex: none; display: inline-block; vertical-align: middle; image-rendering: pixelated; box-shadow: 0 0 0 1px var(--shadow); }
</style>
