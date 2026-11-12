<!--
  Retro channel logo: one of the 18 backgrounds (2 variants × the numbers
  1–9, cut from assets/channel-logos) with the channel name written over it,
  each with the typeface and effects of the reference boards
  (assets/channel-logos/ref-*.jpg). Sizes are in container units, so the
  same logo renders in the TV grid and in the phone preview.
  Long names shrink to fit the tile.
-->
<script lang="ts">
  let { number, name, variant = 1 }: { number: number; name: string; variant?: number } = $props();

  const v = $derived(variant === 2 ? 2 : 1);
  const n = $derived(Math.min(9, Math.max(1, Math.round(number))));

  let box: HTMLElement | undefined = $state();
  let text: HTMLElement | undefined = $state();
  let fit = $state(1);

  // Natural width at fit = 1 is the drawn width / fit (the rect includes the
  // rotation or skew of the style); shrink when it overflows.
  function measure() {
    if (!box || !text) return;
    const natural = text.getBoundingClientRect().width / fit;
    const room = box.getBoundingClientRect().width;
    if (!natural || !room) return;
    fit = Math.min(1, room / natural);
  }

  $effect(() => {
    void name;
    void v;
    void n;
    fit = 1;
    queueMicrotask(measure);
    document.fonts?.ready.then(measure).catch(() => {});
  });
</script>

<div class="logo s{v}-{n}" style:background-image="url(/img/channels/v{v}/{n}.webp)">
  <div class="name" bind:this={box}>
    <span bind:this={text} style:--fit={fit}>{name}</span>
  </div>
</div>

<style>
  @font-face {
    font-family: 'Logo Chrome';
    src: url('/fonts/Exo2-BlackItalic.woff2') format('woff2');
  }
  @font-face {
    font-family: 'Logo Condensed';
    src: url('/fonts/Oswald-Medium.woff2') format('woff2');
  }
  @font-face {
    font-family: 'Logo Didone';
    src: url('/fonts/LibreBodoni-Medium.woff2') format('woff2');
  }
  @font-face {
    font-family: 'Logo Roman';
    src: url('/fonts/Cinzel-Medium.woff2') format('woff2');
  }
  @font-face {
    font-family: 'Logo Brush';
    src: url('/fonts/KaushanScript.woff2') format('woff2');
  }
  @font-face {
    font-family: 'Logo Pixel';
    src: url('/fonts/Silkscreen-Bold.woff2') format('woff2');
  }
  @font-face {
    font-family: 'Logo Dots';
    src: url('/fonts/Doto-Black.woff2') format('woff2');
  }
  @font-face {
    font-family: 'Logo Techno';
    src: url('/fonts/Audiowide.woff2') format('woff2');
  }

  .logo {
    position: relative;
    width: 100%;
    height: 100%;
    container-type: inline-size;
    background-size: cover;
    background-position: center;
    overflow: hidden;
  }
  .name {
    position: absolute;
    left: 6%;
    right: 6%;
    top: var(--y, 5%);
    display: flex;
    justify-content: center;
    white-space: nowrap;
    line-height: 1.1;
    /* blends the text into the picture instead of looking pasted on */
    filter: blur(0.12cqw) var(--drop, drop-shadow(0 0.6cqw 0.4cqw rgba(0, 0, 0, 0.85)));
  }
  .name span {
    display: inline-block;
    padding: 0 0.25em;
    font-size: calc(var(--size, 13cqw) * var(--fit, 1));
    font-family: 'Logo Chrome', sans-serif;
    text-transform: uppercase;
    color: #fff;
    transform: var(--tf, none);
  }

  /* Chrome (most italic sans logos) ------------------------------------------- */
  .s1-1 .name span,
  .s1-4 .name span,
  .s1-5 .name span,
  .s1-9 .name span,
  .s2-1 .name span,
  .s2-5 .name span,
  .s2-7 .name span {
    background: linear-gradient(180deg, #ffffff 0%, #dfe3f7 46%, #3d4270 50%, #8a90bd 62%, #e9ebff 88%, #ffffff 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }
  .s1-1 {
    --y: 5%;
    --size: 14cqw;
  }
  .s1-2 {
    --y: 4.5%;
    --size: 16cqw;
  }
  .s1-2 .name span {
    font-family: 'Logo Condensed', sans-serif;
    color: #f4e4c4;
    transform: scaleY(1.3);
  }
  .s1-3 {
    --y: 4.5%;
    --size: 17cqw;
    --tf: rotate(-7deg);
  }
  .s1-3 .name span,
  .s2-3 .name span {
    font-family: 'Logo Brush', cursive;
    text-transform: none;
    color: #e8399c;
    padding-bottom: 0.1em;
    -webkit-text-stroke: 0.025em currentColor;
    background: linear-gradient(90deg, transparent 2%, #e8399c 6%, #ff6fbf 60%, transparent 96%) no-repeat 0 100% /
      100% 0.11em;
  }
  .s1-4 {
    --y: 74.5%;
    --size: 14.5cqw;
  }
  .s1-5 {
    --y: 6%;
    --size: 14cqw;
  }
  .s1-6 {
    --y: 69%;
    --size: 13cqw;
  }
  .s1-6 .name span {
    font-family: 'Logo Techno', sans-serif;
    transform: skewX(-12deg);
    background: linear-gradient(180deg, #ffffff 0%, #e4e6f4 46%, #5a5e80 52%, #b9bcd8 70%, #ffffff 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }
  .s1-7 {
    --y: 4%;
    --size: 13cqw;
  }
  .s1-7 .name span {
    font-family: 'Logo Pixel', monospace;
    color: #e2e2e2;
  }
  .s1-7 .name {
    --drop: drop-shadow(0.5cqw 0.5cqw 0 rgba(20, 0, 40, 0.9));
  }
  .s1-8 {
    --y: 3.5%;
    --size: 14cqw;
  }
  .s1-8 .name span {
    font-family: 'Logo Roman', serif;
    color: #ead6b0;
  }
  .s1-9 {
    --y: 65%;
    --size: 13.5cqw;
    --tf: rotate(-6deg);
  }
  .s1-9 .name span {
    background: linear-gradient(180deg, #ffffff 0%, #ddd8ff 44%, #5a4fa0 50%, #9d93e0 66%, #e6e2ff 100%);
    -webkit-background-clip: text;
    background-clip: text;
  }

  /* Variant 2 ---------------------------------------------------------------- */
  .s2-1 {
    --y: 4%;
    --size: 14cqw;
  }
  .s2-1 .name::after {
    content: '';
    position: absolute;
    left: 0;
    right: 0;
    bottom: -0.6cqw;
    height: 0.5cqw;
    background: linear-gradient(90deg, transparent, #dfe2ff 20%, #ffffff 50%, #dfe2ff 80%, transparent);
  }
  .s2-2 {
    --y: 6.5%;
    --size: 15.5cqw;
  }
  .s2-2 .name span {
    color: transparent;
    background: repeating-linear-gradient(180deg, #f6ecd6 0 0.1em, transparent 0.1em 0.135em);
    -webkit-background-clip: text;
    background-clip: text;
  }
  .s2-3 {
    --y: 4.5%;
    --size: 17cqw;
    --tf: rotate(-6deg);
  }
  .s2-3 .name span {
    color: #ff3d8d;
  }
  .s2-4 {
    --y: 5.5%;
    --size: 16cqw;
  }
  .s2-4 .name span {
    font-family: 'Logo Didone', serif;
    color: #efe2c4;
    transform: scaleX(0.8) scaleY(1.3);
  }
  .s2-5 {
    --y: 5%;
    --size: 14cqw;
  }
  .s2-6 {
    --y: 5.5%;
    --size: 15.5cqw;
  }
  .s2-6 .name span {
    font-family: 'Logo Dots', monospace;
    color: #5ff0a8;
  }
  .s2-6 .name {
    --drop: drop-shadow(0 0 1.2cqw rgba(60, 255, 160, 0.75));
  }
  .s2-7 {
    --y: 4%;
    --size: 14cqw;
  }
  .s2-7 .name span::before {
    content: '';
    position: absolute;
    right: 100%;
    top: 22%;
    width: 1.6em;
    height: 58%;
    background: repeating-linear-gradient(180deg, #ffffff 0 0.06em, transparent 0.06em 0.13em);
    -webkit-mask: linear-gradient(90deg, transparent, #000);
    mask: linear-gradient(90deg, transparent, #000);
  }
  .s2-7 .name span {
    position: relative;
  }
  .s2-8 {
    --y: 3.5%;
    --size: 14cqw;
  }
  .s2-8 .name span {
    font-family: 'Logo Roman', serif;
    color: transparent;
    background: linear-gradient(180deg, #ffe7a3 0%, #e0b25a 50%, #a8772a 75%, #f6d68a 100%);
    -webkit-background-clip: text;
    background-clip: text;
  }
  .s2-9 {
    --y: 4%;
    --size: 14cqw;
  }
  .s2-9 .name span {
    color: #f2e8d2;
  }
</style>
