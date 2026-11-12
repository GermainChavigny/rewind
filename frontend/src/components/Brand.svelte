<!--
  The REWIND brand mark, everywhere the name is shown as a logo (TV, phone
  remote, phone settings). It copies the intro video (public/video/intro.webm):
  black bold "REWIND" in a white rounded box, "Video System" in light letters
  under it, with the slight red/blue fringe of a VHS picture.
  `size` is the height of the capitals' box in px; everything scales with it.
  The tagline colour follows `--brand-tag` (white by default, for dark
  backgrounds).
-->
<script lang="ts">
  let { size = 40, tagline = true }: { size?: number; tagline?: boolean } = $props();
</script>

<span class="brand" style:--s="{size}px" aria-label="REWIND">
  <span class="box" aria-hidden="true">REWIND</span>
  {#if tagline}<span class="tagline" aria-hidden="true">Video System</span>{/if}
</span>

<style>
  @font-face {
    font-family: 'Rewind Brand';
    src: url('/fonts/Roboto-Bold.woff2') format('woff2');
    font-weight: 700;
  }
  @font-face {
    font-family: 'Rewind Brand';
    src: url('/fonts/Roboto-Regular.woff2') format('woff2');
    font-weight: 400;
  }
  .brand {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    gap: calc(var(--s) * 0.16);
    font-family: 'Rewind Brand', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1;
    vertical-align: middle;
  }
  .box {
    padding: calc(var(--s) * 0.17) calc(var(--s) * 0.28) calc(var(--s) * 0.13);
    border-radius: calc(var(--s) * 0.12);
    background: #fff;
    color: #000;
    font-weight: 700;
    font-size: calc(var(--s) * 0.78);
    letter-spacing: 0.01em;
    /* VHS chroma fringe, as on the video */
    box-shadow:
      calc(var(--s) * -0.03) 0 0 rgba(255, 40, 60, 0.55),
      calc(var(--s) * 0.03) 0 0 rgba(40, 120, 255, 0.55);
  }
  .tagline {
    color: var(--brand-tag, #fff);
    font-weight: 400;
    font-size: calc(var(--s) * 0.42);
    letter-spacing: 0.09em;
  }
</style>
