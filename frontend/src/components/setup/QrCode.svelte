<!-- A QR code drawn as crisp SVG squares (black on white, with its quiet zone). -->
<script lang="ts">
  import qrcode from 'qrcode-generator';

  let { text, size = 200 }: { text: string; size?: number } = $props();

  const QUIET = 2; // modules of white margin (scanners need some)
  const code = $derived.by(() => {
    const qr = qrcode(0, 'M');
    qr.addData(text);
    qr.make();
    const n = qr.getModuleCount();
    let d = '';
    for (let r = 0; r < n; r++)
      for (let c = 0; c < n; c++) if (qr.isDark(r, c)) d += `M${c + QUIET} ${r + QUIET}h1v1h-1z`;
    return { n: n + 2 * QUIET, d };
  });
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 {code.n} {code.n}"
  shape-rendering="crispEdges"
  role="img"
  aria-label={text}
>
  <rect width={code.n} height={code.n} fill="#fff" />
  <path d={code.d} fill="#000" />
</svg>
