<!--
  Small pictograms drawn on a 16×16 pixel grid (crisp edges, current text
  colour), used instead of emoji / Unicode symbols, which phones draw as
  colourful emoji that clash with the retro look. Sized to the text (1em).
-->
<script module lang="ts">
  export type GlyphName =
    | 'play' | 'pause' | 'playpause' | 'stop' | 'left' | 'right' | 'up' | 'down'
    | 'next' | 'previous' | 'forward' | 'rewind' | 'caret-right' | 'caret-down'
    | 'warn' | 'bolt' | 'check' | 'external' | 'erase' | 'refresh' | 'sun' | 'moon'
    | 'power' | 'plus' | 'minus' | 'bell' | 'gear' | 'home' | 'keyboard'; // prettier-ignore
</script>

<script lang="ts">
  let { name, size = '1em' }: { name: GlyphName; size?: string } = $props();
</script>

<svg
  class="glyph"
  width={size}
  height={size}
  viewBox="0 0 16 16"
  fill="currentColor"
  shape-rendering="crispEdges"
  aria-hidden="true"
>
  {#if name === 'play' || name === 'right'}
    <path d="M4 2 H6 V3 H8 V4 H10 V5 H12 V6 H14 V10 H12 V11 H10 V12 H8 V13 H6 V14 H4 Z" />
  {:else if name === 'left'}
    <path d="M12 2 H10 V3 H8 V4 H6 V5 H4 V6 H2 V10 H4 V11 H6 V12 H8 V13 H10 V14 H12 Z" />
  {:else if name === 'pause'}
    <rect x="3" y="2" width="4" height="12" /><rect x="9" y="2" width="4" height="12" />
  {:else if name === 'playpause'}
    <path d="M1 3 H3 V4 H5 V6 H7 V10 H5 V12 H3 V13 H1 Z" />
    <rect x="9" y="3" width="2" height="10" /><rect x="13" y="3" width="2" height="10" />
  {:else if name === 'stop'}
    <rect x="3" y="3" width="10" height="10" />
  {:else if name === 'up'}
    <path d="M2 12 V10 H3 V8 H4 V6 H5 V4 H6 V2 H10 V4 H11 V6 H12 V8 H13 V10 H14 V12 Z" />
  {:else if name === 'down'}
    <path d="M2 4 V6 H3 V8 H4 V10 H5 V12 H6 V14 H10 V12 H11 V10 H12 V8 H13 V6 H14 V4 Z" />
  {:else if name === 'forward'}
    <path d="M1 3 H3 V5 H5 V6 H7 V10 H5 V11 H3 V13 H1 Z" /><path d="M8 3 H10 V5 H12 V6 H14 V10 H12 V11 H10 V13 H8 Z" />
  {:else if name === 'rewind'}
    <path d="M15 3 H13 V5 H11 V6 H9 V10 H11 V11 H13 V13 H15 Z" /><path d="M8 3 H6 V5 H4 V6 H2 V10 H4 V11 H6 V13 H8 Z" />
  {:else if name === 'next'}
    <path d="M1 3 H3 V5 H5 V7 H6 V9 H5 V11 H3 V13 H1 Z" /><path d="M6 3 H8 V5 H10 V7 H11 V9 H10 V11 H8 V13 H6 Z" />
    <rect x="12" y="3" width="2" height="10" />
  {:else if name === 'previous'}
    <path d="M15 3 H13 V5 H11 V7 H10 V9 H11 V11 H13 V13 H15 Z" /><path d="M10 3 H8 V5 H6 V7 H5 V9 H6 V11 H8 V13 H10 Z" />
    <rect x="2" y="3" width="2" height="10" />
  {:else if name === 'caret-right'}
    <path d="M5 3 H7 V5 H9 V7 H11 V9 H9 V11 H7 V13 H5 Z" />
  {:else if name === 'caret-down'}
    <path d="M3 5 V7 H5 V9 H7 V11 H9 V9 H11 V7 H13 V5 Z" />
  {:else if name === 'warn'}
    <path d="M7 1 H9 V3 H10 V5 H11 V7 H12 V9 H13 V11 H14 V13 H15 V15 H1 V13 H2 V11 H3 V9 H4 V7 H5 V5 H6 V3 H7 Z" />
    <rect x="7" y="5" width="2" height="5" fill="var(--glyph-cut, #fff)" />
    <rect x="7" y="11" width="2" height="2" fill="var(--glyph-cut, #fff)" />
  {:else if name === 'bolt'}
    <path d="M9 1 H12 L9 7 H13 L6 15 H5 L7 9 H3 Z" shape-rendering="auto" />
  {:else if name === 'check'}
    <path d="M2 8 H4 V9 H5 V10 H6 V9 H7 V8 H8 V7 H9 V6 H10 V5 H11 V4 H12 V3 H14 V5 H13 V6 H12 V7 H11 V8 H10 V9 H9 V10 H8 V11 H7 V12 H5 V11 H4 V10 H3 V9 H2 Z" />
  {:else if name === 'external'}
    <path d="M2 4 H8 V6 H4 V12 H10 V8 H12 V14 H2 Z" />
    <path d="M9 2 H14 V7 H12 V5 H11 V6 H10 V7 H9 V8 H8 V9 H7 V7 H8 V6 H9 V5 H10 V4 H9 Z" />
  {:else if name === 'erase'}
    <path d="M5 3 H15 V13 H5 V12 H4 V11 H3 V10 H2 V9 H1 V7 H2 V6 H3 V5 H4 V4 H5 Z" />
    <path d="M7 5 H9 V6 H10 V5 H12 V7 H11 V9 H12 V11 H10 V10 H9 V11 H7 V9 H8 V7 H7 Z" fill="var(--glyph-cut, #fff)" />
  {:else if name === 'refresh'}
    <path d="M5 2 H11 V3 H12 V1 H14 V7 H8 V5 H10 V4 H6 V5 H5 V6 H4 V10 H5 V11 H6 V12 H10 V11 H11 V10 H13 V12 H12 V13 H11 V14 H5 V13 H4 V12 H3 V11 H2 V5 H3 V4 H4 V3 H5 Z" />
  {:else if name === 'sun'}
    <path d="M6 4 H10 V5 H11 V6 H12 V10 H11 V11 H10 V12 H6 V11 H5 V10 H4 V6 H5 V5 H6 Z" />
    <rect x="7" y="0" width="2" height="3" /><rect x="7" y="13" width="2" height="3" />
    <rect x="0" y="7" width="3" height="2" /><rect x="13" y="7" width="3" height="2" />
    <rect x="2" y="2" width="2" height="2" /><rect x="12" y="2" width="2" height="2" />
    <rect x="2" y="12" width="2" height="2" /><rect x="12" y="12" width="2" height="2" />
  {:else if name === 'moon'}
    <path d="M6 1 H10 V2 H8 V3 H7 V5 H6 V11 H7 V13 H8 V14 H10 V15 H6 V14 H4 V13 H3 V12 H2 V10 H1 V6 H2 V4 H3 V3 H4 V2 H6 Z" />
  {:else if name === 'power'}
    <path d="M7 1 H9 V8 H7 Z" />
    <path d="M4 3 H6 V5 H5 V6 H4 V10 H5 V11 H6 V12 H10 V11 H11 V10 H12 V6 H11 V5 H10 V3 H12 V4 H13 V5 H14 V11 H13 V12 H12 V13 H11 V14 H5 V13 H4 V12 H3 V11 H2 V5 H3 V4 H4 Z" />
  {:else if name === 'plus'}
    <rect x="7" y="2" width="2" height="12" /><rect x="2" y="7" width="12" height="2" />
  {:else if name === 'minus'}
    <rect x="2" y="7" width="12" height="2" />
  {:else if name === 'gear'}
    <path fill-rule="evenodd" d="M5 3 H11 V4 H12 V5 H13 V11 H12 V12 H11 V13 H5 V12 H4 V11 H3 V5 H4 V4 H5 Z M7 6 H9 V7 H10 V9 H9 V10 H7 V9 H6 V7 H7 Z" />
    <rect x="7" y="1" width="2" height="2" /><rect x="7" y="13" width="2" height="2" />
    <rect x="1" y="7" width="2" height="2" /><rect x="13" y="7" width="2" height="2" />
    <rect x="2" y="2" width="2" height="2" /><rect x="12" y="2" width="2" height="2" />
    <rect x="2" y="12" width="2" height="2" /><rect x="12" y="12" width="2" height="2" />
  {:else if name === 'home'}
    <path d="M7 1 H9 V2 H10 V3 H11 V4 H12 V5 H13 V6 H14 V8 H2 V6 H3 V5 H4 V4 H5 V3 H6 V2 H7 Z" />
    <path d="M3 8 H13 V15 H9 V11 H7 V15 H3 Z" />
  {:else if name === 'keyboard'}
    <path fill-rule="evenodd" d="M1 4 H15 V13 H1 Z M3 6 V8 H5 V6 Z M6 6 V8 H8 V6 Z M9 6 V8 H11 V6 Z M12 6 V8 H13 V6 Z M4 10 V11 H12 V10 Z" />
  {:else if name === 'bell'}
    <path d="M7 1 H9 V2 H11 V3 H12 V5 H13 V10 H14 V12 H2 V10 H3 V5 H4 V3 H5 V2 H7 Z" />
    <rect x="6" y="13" width="4" height="2" />
  {/if}
</svg>

<style>
  .glyph {
    display: inline-block;
    flex: 0 0 auto;
    vertical-align: -0.12em;
  }
</style>
