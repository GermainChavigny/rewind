// Dev-only sheet (not built): /dev/logos.html?name=DEMO-TV shows the 18 retro
// logos, each under the matching cell of the reference boards.
import { mount } from 'svelte';
import ChannelLogo from '../src/components/ChannelLogo.svelte';

const params = new URLSearchParams(location.search);
const name = params.get('name') ?? 'DEMO-TV';
const refs = params.get('refs') !== '0';
const sheet = document.getElementById('sheet')!;
for (const variant of [1, 2]) {
  if (refs)
    for (let n = 1; n <= 9; n++) {
      const ref = document.createElement('div');
      ref.className = 'ref';
      const [row, col] = [Math.floor((n - 1) / 3), (n - 1) % 3];
      ref.style.backgroundImage = `url(/dev/ref-${variant}.jpg)`;
      ref.style.backgroundPosition = `${col * 50}% ${row * 50}%`;
      sheet.append(ref);
    }
  for (let n = 1; n <= 9; n++) {
    const cell = document.createElement('div');
    cell.className = 'cell';
    sheet.append(cell);
    mount(ChannelLogo, { target: cell, props: { number: n, name, variant } });
  }
}
