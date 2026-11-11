/**
 * Spoken feedback (alarm). Uses speech synthesis when a voice for the UI
 * language exists, else recorded clips (audio/<lang>/*.mp3, audio/numbers).
 */

let audio: HTMLAudioElement | null = null;

function frenchVoice(): SpeechSynthesisVoice | undefined {
  const voices = speechSynthesis.getVoices();
  return voices.find((v) => v.name === 'Google français') ?? voices.find((v) => v.lang.startsWith('fr'));
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
  const voice = frenchVoice();
  if (!voice) return false;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.voice = voice;
  u.volume = volume;
  speechSynthesis.speak(u);
  return true;
}

/** "Réveil activé" / "Pas de réveil". */
export function announce(text: string, clip: string, volume = 0.8): void {
  if (!speak(text, volume)) void play(`audio/fr/${clip}.mp3`, volume);
}

/** Speaks a time like "7:30" (clips fallback: hour then minutes). */
export async function announceTime(hhmm: string, volume = 0.8): Promise<void> {
  const [h, m] = hhmm.split(':').map(Number);
  if (speak(`${h}:${String(m).padStart(2, '0')}`, volume)) return;
  await play(`audio/numbers/${h}.wav`, volume);
  if (m > 0) await play(`audio/numbers/${m}.wav`, volume);
}
