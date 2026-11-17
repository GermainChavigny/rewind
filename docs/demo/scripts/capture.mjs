/**
 * Captures a running REWIND for the README demo video (screenshots in
 * captures/, see README.md). It drives the TV page, the phone remote and the
 * admin like a viewer would. Use a sandbox instance: it sets the alarm,
 * plays a movie and sends a (fake) shutdown.
 *
 *   REWIND_URL=http://127.0.0.1:8081 REWIND_PIN=1234 CHROMIUM=/usr/bin/chromium \
 *     node scripts/capture.mjs [intro channels movies series advisor alarm weather phone end]
 */
import { chromium } from 'playwright-core';
import fs from 'fs';
const BASE = process.env.REWIND_URL ?? 'http://127.0.0.1:8081';
const OUT = 'captures';
const pin = process.env.REWIND_PIN ?? '';
const only = process.argv.slice(2);
const want = (s) => !only.length || only.includes(s);
fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM ?? '/usr/bin/chromium',
  args: ['--autoplay-policy=no-user-gesture-required'],
});
// Full brightness: the TV's darkness veil would dim every capture.
await fetch(BASE + '/api/state', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: '{"darkness": 0}' });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const api = (method, path, body) => fetch(BASE + path, { method, headers: { 'Content-Type': 'application/json', 'X-Rewind-Pin': pin }, body: body && JSON.stringify(body) });
async function tvPage() {
  const p = await browser.newPage({ viewport: { width: 960, height: 720 } });
  await p.addInitScript(() => document.addEventListener('DOMContentLoaded', () => {
    const st = document.createElement('style');
    st.textContent = '.cursor { display: none !important; }';
    document.head.append(st);
  }));
  await p.goto(BASE + '/');
  await wait(2500);
  return p;
}
const shot = (p, name) => p.screenshot({ path: `${OUT}/${name}.png` }).then(() => console.log('shot', name));

if (want('intro')) {
  const p = await tvPage();
  for (const ms of [0, 1500, 3000]) { await wait(ms ? 1500 : 0); await shot(p, `intro-${ms}`); }
  await p.close();
}
if (want('channels')) {
  const p = await tvPage();
  // The grid over black: the channel starting behind it shows YouTube's title bar.
  await p.addStyleTag({ content: '.video, iframe { display: none !important; }' });
  await p.keyboard.press('5'); await wait(1000); await shot(p, 'grid');
  await p.addStyleTag({ content: '.video, iframe { display: block !important; }' });
  await wait(9000); await shot(p, 'billiard');
  await p.keyboard.press('2'); await wait(9000); await shot(p, 'basketball');
  await p.evaluate(() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'AudioVolumeUp' }))); await wait(200);
  await p.evaluate(() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'AudioVolumeUp' }))); await wait(400); await shot(p, 'basketball-volume');
  await p.close();
}
if (want('movies')) {
  const p = await tvPage();
  await p.keyboard.press('9'); await wait(4000); await shot(p, 'library');
  await p.locator('.row', { hasText: 'Demolition Man' }).click(); await wait(1500); await shot(p, 'demolition-detail');
  await p.locator('.detail .crt-btn.primary').click(); await wait(8000); await shot(p, 'demolition-playing');
  await p.keyboard.press(' '); await wait(1500); await shot(p, 'demolition-pause');
  await p.keyboard.press(' '); await wait(500);
  await p.locator('.row', { hasText: 'Demolition Man' }).count();
  await p.close();
}
if (want('series')) {
  const p = await tvPage();
  await p.keyboard.press('9'); await wait(4000);
  await p.locator('.tabs button').nth(1).click(); await wait(1000);
  await p.locator('.row', { hasText: 'Simpsons' }).click(); await wait(1500); await shot(p, 'series-detail');
  await p.close();
}
if (want('advisor')) {
  const p = await tvPage();
  await p.keyboard.press('9'); await wait(4000);
  await p.getByRole('button', { name: 'Advisor' }).click(); await wait(3000);
  for (const [crit, opt] of [['Mood', 'Adrenaline'], ['Era', '90s'], ['Rating', 'Must watch'], ['Theme 1', 'Sci-Fi']]) {
    await p.locator('.crit', { has: p.locator('.c-name', { hasText: new RegExp(`^${crit}$`) }) }).click(); await wait(500);
    await p.locator('.opt', { hasText: new RegExp(`^${opt}$`) }).click(); await wait(500);
  }
  await p.mouse.move(-10, -10); await wait(1500); await shot(p, 'advisor-criteria');
  await p.getByRole('button', { name: 'Search', exact: true }).last().click(); await wait(700); await shot(p, 'advisor-thinking');
  await p.locator('.rec').first().waitFor({ timeout: 90000 }); await wait(3000); await shot(p, 'advisor-results');
  await p.close();
}
if (want('alarm')) {
  const p = await tvPage();
  await p.keyboard.press('5'); await wait(4000);
  const now = new Date(Date.now() + 60000);
  const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  const before = await (await api('GET', '/api/alarm')).json();
  await api('PUT', '/api/alarm', { ...before, time, enabled: true });
  await p.reload(); await wait(3000);
  await p.waitForFunction(() => document.body.innerText.includes('Wake up!'), null, { timeout: 130000 });
  await wait(15000); await shot(p, 'alarm-ringing'); await wait(500); await shot(p, 'alarm-ringing-2');
  await p.keyboard.press('Shift'); await wait(1500);
  await api('PUT', '/api/alarm', { ...before, time: '07:00', enabled: true });
  await p.reload(); await wait(3000);
  await p.keyboard.press('5'); await wait(10000);
  await p.keyboard.press('ArrowUp'); await wait(400); await shot(p, 'alarm-osd');
  await wait(3500);
  await p.keyboard.press(' '); await wait(1500);
  await p.locator('button.alarm').click(); await p.mouse.move(480, 700); await wait(2500); await shot(p, 'alarm-screen');
  await api('PUT', '/api/alarm', before);
  await p.close();
}
if (want('weather')) {
  const p = await tvPage();
  await p.keyboard.press('5'); await wait(6000);
  await p.keyboard.press('5'); await wait(600);
  await p.locator('button.weather').click(); await p.mouse.move(480, 360); await wait(5000);
  await p.addStyleTag({ content: '.video, .pause-dim { visibility: hidden !important; }' }); await wait(300);
  await shot(p, 'weather');
  await p.close();
}
if (want('phone')) {
  const ph = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  await ph.addInitScript((p) => sessionStorage.setItem('rewind-admin-pin', p), pin);
  await ph.goto(BASE + '/remote/'); await wait(2500); await shot(ph, 'remote');
  await ph.goto(BASE + '/admin/'); await wait(2500); await shot(ph, 'admin-menu');
  await ph.getByText('Channels', { exact: true }).click(); await wait(1000); await shot(ph, 'admin-channels');
  await ph.locator('.tile').nth(4).click(); await wait(1200); await shot(ph, 'admin-channel-edit');
  await ph.getByText('Cancel').click(); await wait(600);
  await ph.getByText('Alarm', { exact: true }).click(); await wait(1000); await shot(ph, 'admin-alarm');
  await ph.close();
}
if (want('end')) {
  const p = await tvPage();
  await p.keyboard.press('5'); await wait(5000);
  await api('POST', '/api/remote/shutdown');
  await wait(4000); await shot(p, 'end');
  await p.close();
}
await browser.close();
