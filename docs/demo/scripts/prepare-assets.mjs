/**
 * Copies the files the video borrows from the app (music, cursors, alarm
 * chime) into public/, and downloads the VCR OSD Mono font. Plain Node, so it
 * runs the same on Windows, macOS and Linux. Run from docs/demo:
 *   node scripts/prepare-assets.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import zlib from 'node:zlib';

const DEMO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const REPO = path.resolve(DEMO, '..', '..');
const PUBLIC = path.join(DEMO, 'public');
const FONT_URL = 'https://dl.dafont.com/dl/?f=vcr_osd_mono';

function copy(from, to) {
  fs.mkdirSync(path.dirname(to), { recursive: true });
  fs.copyFileSync(from, to);
  console.log('copied', path.relative(REPO, from));
}

copy(path.join(REPO, 'assets', 'background.mp3'), path.join(PUBLIC, 'background.mp3'));
for (const name of ['cursor.png', 'pointer.png'])
  copy(path.join(REPO, 'frontend', 'public', 'cursors', name), path.join(PUBLIC, 'cursors', name));
copy(path.join(REPO, 'frontend', 'public', 'audio', 'chimes', 'bells.mp3'), path.join(PUBLIC, 'sfx', 'bells.mp3'));

/** The first .ttf file of a zip archive (read through its central directory). */
function ttfFromZip(zip) {
  const eocd = zip.lastIndexOf(Buffer.from([0x50, 0x4b, 0x05, 0x06]));
  if (eocd < 0) throw new Error('not a zip file');
  const entries = zip.readUInt16LE(eocd + 10);
  let p = zip.readUInt32LE(eocd + 16);
  for (let i = 0; i < entries; i++) {
    const method = zip.readUInt16LE(p + 10);
    const size = zip.readUInt32LE(p + 20);
    const nameLength = zip.readUInt16LE(p + 28);
    const extraLength = zip.readUInt16LE(p + 30);
    const commentLength = zip.readUInt16LE(p + 32);
    const local = zip.readUInt32LE(p + 42);
    const name = zip.toString('utf8', p + 46, p + 46 + nameLength);
    if (name.toLowerCase().endsWith('.ttf')) {
      const start = local + 30 + zip.readUInt16LE(local + 26) + zip.readUInt16LE(local + 28);
      const data = zip.subarray(start, start + size);
      return method === 8 ? zlib.inflateRawSync(data) : data;
    }
    p += 46 + nameLength + extraLength + commentLength;
  }
  throw new Error('no .ttf in the archive');
}

const font = path.join(PUBLIC, 'fonts', 'vcr-osd-mono.ttf');
if (fs.existsSync(font)) {
  console.log('font already there');
} else {
  const res = await fetch(FONT_URL);
  if (!res.ok) throw new Error(`font download failed: HTTP ${res.status}`);
  fs.mkdirSync(path.dirname(font), { recursive: true });
  fs.writeFileSync(font, ttfFromZip(Buffer.from(await res.arrayBuffer())));
  console.log('downloaded VCR OSD Mono');
}
