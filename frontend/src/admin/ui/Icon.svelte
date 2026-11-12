<!-- Flat 32×32 desktop icons for the settings menu, black outlines, few colours. -->
<script lang="ts">
  let { name, size = 40 }: { name: string; size?: number } = $props();
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 32 32"
  fill="none"
  stroke="#000"
  stroke-width="2"
  stroke-linejoin="miter"
  shape-rendering="crispEdges"
  aria-hidden="true"
>
  {#if name === 'channels'}
    <rect x="3" y="3" width="8" height="8" fill="#f3ec3a" />
    <rect x="12" y="3" width="8" height="8" fill="#e8399c" />
    <rect x="21" y="3" width="8" height="8" fill="#38c7e8" />
    <rect x="3" y="12" width="8" height="8" fill="#ff7a1a" />
    <rect x="12" y="12" width="8" height="8" fill="#fff" />
    <rect x="21" y="12" width="8" height="8" fill="#5ff0a8" />
    <rect x="3" y="21" width="8" height="8" fill="#8f86e0" />
    <rect x="12" y="21" width="8" height="8" fill="#f3ec3a" />
    <rect x="21" y="21" width="8" height="8" fill="#e8399c" />
  {:else if name === 'remote'}
    <rect x="10" y="2" width="12" height="28" fill="#4a4a46" />
    <rect x="13" y="5" width="6" height="3" fill="#e8001b" />
    <rect x="13" y="11" width="2" height="2" fill="#fff" stroke-width="1" />
    <rect x="17" y="11" width="2" height="2" fill="#fff" stroke-width="1" />
    <rect x="13" y="15" width="2" height="2" fill="#fff" stroke-width="1" />
    <rect x="17" y="15" width="2" height="2" fill="#fff" stroke-width="1" />
    <rect x="13" y="19" width="2" height="2" fill="#fff" stroke-width="1" />
    <rect x="17" y="19" width="2" height="2" fill="#fff" stroke-width="1" />
    <rect x="13" y="24" width="6" height="3" fill="#38c7e8" stroke-width="1" />
  {:else if name === 'tv'}
    <rect x="3" y="6" width="26" height="19" fill="#8d8d86" />
    <rect x="6" y="9" width="16" height="13" fill="#2340c8" />
    <rect x="24" y="10" width="3" height="3" fill="#f3ec3a" stroke-width="1" />
    <rect x="24" y="16" width="3" height="3" fill="#e8001b" stroke-width="1" />
    <path d="M10 2 L16 6 L22 2" />
    <path d="M8 25 V29 M24 25 V29" />
  {:else if name === 'weather'}
    <circle cx="12" cy="11" r="6" fill="#f3ec3a" shape-rendering="auto" />
    <path d="M12 1 V3 M12 19 V21 M2 11 H4 M20 11 H22 M5 4 L6 5 M19 4 L18 5" />
    <path d="M10 27 H27 A4 4 0 0 0 27 19 A6 6 0 0 0 15 18 A5 5 0 0 0 10 27 Z" fill="#fff" shape-rendering="auto" />
  {:else if name === 'picture'}
    <rect x="3" y="5" width="26" height="20" fill="#fff" />
    <rect x="5" y="7" width="22" height="16" fill="#38c7e8" stroke="none" />
    <path d="M5 23 L12 14 L17 19 L21 15 L27 23 Z" fill="#08852a" />
    <circle cx="22" cy="11" r="2" fill="#f3ec3a" stroke-width="1" shape-rendering="auto" />
    <path d="M10 29 H22" />
  {:else if name === 'alarm'}
    <circle cx="16" cy="18" r="10" fill="#fff" shape-rendering="auto" />
    <path d="M16 12 V18 H21" />
    <path d="M4 7 L9 3 M28 7 L23 3" stroke-width="3" />
    <path d="M9 28 L7 30 M23 28 L25 30" />
  {:else if name === 'library'}
    <rect x="3" y="7" width="26" height="18" fill="#2b2b2b" />
    <path d="M3 11 H29 M3 21 H29" stroke="#fff" stroke-width="1" />
    <path d="M6 8 V10 M10 8 V10 M14 8 V10 M18 8 V10 M22 8 V10 M26 8 V10" stroke="#fff" />
    <path d="M6 22 V24 M10 22 V24 M14 22 V24 M18 22 V24 M22 22 V24 M26 22 V24" stroke="#fff" />
    <path d="M13 13 L20 16 L13 19 Z" fill="#f3ec3a" stroke-width="1" />
  {:else if name === 'lock'}
    <path d="M10 14 V9 A6 6 0 0 1 22 9 V14" shape-rendering="auto" stroke-width="3" />
    <rect x="6" y="14" width="20" height="15" fill="#f3ec3a" />
    <rect x="15" y="19" width="2" height="5" fill="#000" />
  {/if}
</svg>
