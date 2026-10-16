/**
 * Tiny synthesized sound effects (Web Audio) — no audio files, works offline.
 * Volumes are kept deliberately low.
 */
let audioContext = null;

function getContext() {
  if (typeof window === 'undefined') return null;
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtx) return null;
  audioContext ??= new AudioCtx();
  if (audioContext.state === 'suspended') audioContext.resume().catch(() => {});
  return audioContext;
}

function tone(ctx, { frequency, start = 0, duration = 0.15, volume = 0.06, type = 'sine' }) {
  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();
  const startAt = ctx.currentTime + start;
  oscillator.type = type;
  oscillator.frequency.setValueAtTime(frequency, startAt);
  gain.gain.setValueAtTime(0.0001, startAt);
  gain.gain.exponentialRampToValueAtTime(volume, startAt + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, startAt + duration);
  oscillator.connect(gain).connect(ctx.destination);
  oscillator.start(startAt);
  oscillator.stop(startAt + duration + 0.05);
}

const SOUNDS = {
  gain: [
    { frequency: 880, duration: 0.09 },
    { frequency: 1320, start: 0.07, duration: 0.14 },
  ],
  loss: [
    { frequency: 440, duration: 0.12, type: 'triangle' },
    { frequency: 330, start: 0.1, duration: 0.18, type: 'triangle' },
  ],
  leader: [
    { frequency: 660, duration: 0.12 },
    { frequency: 880, start: 0.11, duration: 0.12 },
    { frequency: 1320, start: 0.22, duration: 0.3 },
  ],
  reveal: [{ frequency: 523, duration: 0.25, type: 'triangle', volume: 0.07 }],
  victory: [
    { frequency: 523, duration: 0.18, type: 'triangle', volume: 0.08 },
    { frequency: 659, start: 0.16, duration: 0.18, type: 'triangle', volume: 0.08 },
    { frequency: 784, start: 0.32, duration: 0.18, type: 'triangle', volume: 0.08 },
    { frequency: 1047, start: 0.48, duration: 0.6, type: 'triangle', volume: 0.09 },
  ],
};

export function playSound(name) {
  const ctx = getContext();
  const notes = SOUNDS[name];
  if (!ctx || !notes) return;
  notes.forEach((note) => tone(ctx, note));
}
