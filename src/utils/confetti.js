import confetti from 'canvas-confetti';

const BRAND_CONFETTI = ['#C4073D', '#F8F3EC', '#F5921E', '#1F6FE0', '#FFC83D'];

export function burstConfetti({ colors = BRAND_CONFETTI, origin = { x: 0.5, y: 0.55 } } = {}) {
  confetti({ particleCount: 90, spread: 80, startVelocity: 45, origin, colors, scalar: 1.1 });
}

export function celebrationConfetti(durationMs = 3200, colors = BRAND_CONFETTI) {
  const end = Date.now() + durationMs;
  burstConfetti({ colors, origin: { x: 0.5, y: 0.45 } });
  (function frame() {
    confetti({ particleCount: 5, angle: 60, spread: 60, origin: { x: 0, y: 0.7 }, colors, scalar: 1.2 });
    confetti({ particleCount: 5, angle: 120, spread: 60, origin: { x: 1, y: 0.7 }, colors, scalar: 1.2 });
    if (Date.now() < end) requestAnimationFrame(frame);
  })();
}
