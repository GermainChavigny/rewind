/**
 * Spoken feedback (alarm). Uses speech synthesis when a voice for the UI
 * language exists, else recorded clips (audio/<lang>/*.mp3, audio/numbers),
 * which only exist in French for now.
 */
import { language } from './i18n';

let audio: HTMLAudioElement | null = null;

/** Recorded clips: language → folder (the numbers are spoken in French). */
const CLIPS = new Set(['fr']);

function voiceFor(lang: string): SpeechSynthesisVoice | undefined {
  const voices = speechSynthesis.getVoices().filter((v) => v.lang.toLowerCase().startsWith(lang));
  // Google voices sound best in Chromium ("Google français", "Google US English").
  return voices.find((v) => v.name.startsWith('Google')) ?? voices[0];
}

function play(src: string, volume: number): Promise<void> {
  audio ??= new Audio();
  audio.src = src;
  audio.volume = volume;
  return new Promise((resolve) => {
    audio!.onended = () => resolve();
    audio!.onerror = () => resolve();
    audio!.play().catch(() => resolve());
  });
}

function speak(text: string, volume: number): boolean {
  const voice = voiceFor(language());
  if (!voice) return false;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.voice = voice;
  u.volume = volume;
  speechSynthesis.speak(u);
  return true;
}

/** "Réveil activé" / "Pas de réveil" / "Film prêt" (recorded clip as a fallback, if any). */
export function announce(text: string, clip?: string, volume = 0.8): void {
  const lang = language();
  if (!speak(text, volume) && clip && CLIPS.has(lang)) void play(`audio/${lang}/${clip}.mp3`, volume);
}

/** Speaks a time like "7:30" (clips fallback: hour then minutes). */
export async function announceTime(hhmm: string, volume = 0.8): Promise<void> {
  const [h, m] = hhmm.split(':').map(Number);
  if (speak(`${h}:${String(m).padStart(2, '0')}`, volume) || !CLIPS.has(language())) return;
  await play(`audio/numbers/${h}.wav`, volume);
  if (m > 0) await play(`audio/numbers/${m}.wav`, volume);
}
