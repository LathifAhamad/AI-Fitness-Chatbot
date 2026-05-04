// ============================================================
// GLOWING CURSOR — Neon trail effect that follows mouse
// ============================================================

class GlowCursor {
  constructor() {
    // Don't init on touch devices
    if ('ontouchstart' in window) return;

    this.coords = [];
    this.maxTrail = 25;
    this.mouse = { x: 0, y: 0 };
    this.isMoving = false;
    this.moveTimeout = null;
    this.hue = 180; // Start at cyan
    this.container = null;
    this.dots = [];

    this.init();
  }

  init() {
    // Create container
    this.container = document.createElement('div');
    this.container.className = 'cursor-glow-container';
    this.container.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 99999;
      overflow: hidden;
    `;
    document.body.appendChild(this.container);

    // Create trail dots
    for (let i = 0; i < this.maxTrail; i++) {
      const dot = document.createElement('div');
      const size = Math.max(3, 18 - i * 0.6);
      dot.style.cssText = `
        position: absolute;
        width: ${size}px;
        height: ${size}px;
        border-radius: 50%;
        pointer-events: none;
        transition: opacity 0.3s ease;
        will-change: transform;
      `;
      this.container.appendChild(dot);
      this.dots.push(dot);
      this.coords.push({ x: 0, y: 0 });
    }

    // Main cursor glow
    this.mainGlow = document.createElement('div');
    this.mainGlow.style.cssText = `
      position: absolute;
      width: 40px;
      height: 40px;
      border-radius: 50%;
      pointer-events: none;
      will-change: transform;
      transition: opacity 0.3s ease;
    `;
    this.container.appendChild(this.mainGlow);

    this.addEventListeners();
    this.animate();
  }

  addEventListeners() {
    document.addEventListener('mousemove', (e) => {
      this.mouse.x = e.clientX;
      this.mouse.y = e.clientY;
      this.isMoving = true;

      clearTimeout(this.moveTimeout);
      this.moveTimeout = setTimeout(() => {
        this.isMoving = false;
      }, 100);
    });

    document.addEventListener('mousedown', () => {
      this.mainGlow.style.transform = `translate(${this.mouse.x - 30}px, ${this.mouse.y - 30}px) scale(1.5)`;
    });

    document.addEventListener('mouseup', () => {
      this.mainGlow.style.transform = `translate(${this.mouse.x - 20}px, ${this.mouse.y - 20}px) scale(1)`;
    });
  }

  animate() {
    // Shift hue for color cycling
    this.hue = (this.hue + 0.3) % 360;

    // Update trail positions with smooth following
    let prevX = this.mouse.x;
    let prevY = this.mouse.y;

    this.coords.forEach((coord, i) => {
      const speed = 0.35 - (i * 0.008);
      coord.x += (prevX - coord.x) * speed;
      coord.y += (prevY - coord.y) * speed;
      prevX = coord.x;
      prevY = coord.y;

      const dot = this.dots[i];
      const opacity = this.isMoving ? (1 - i / this.maxTrail) * 0.7 : 0;
      const dotHue = (this.hue + i * 8) % 360;
      const size = Math.max(3, 18 - i * 0.6);

      dot.style.transform = `translate(${coord.x - size / 2}px, ${coord.y - size / 2}px)`;
      dot.style.background = `hsl(${dotHue}, 100%, 65%)`;
      dot.style.boxShadow = `
        0 0 ${6 + (this.maxTrail - i)}px hsl(${dotHue}, 100%, 65%),
        0 0 ${12 + (this.maxTrail - i) * 2}px hsl(${dotHue}, 100%, 50%)
      `;
      dot.style.opacity = opacity;
    });

    // Main glow
    const glowOpacity = this.isMoving ? 0.25 : 0.1;
    this.mainGlow.style.transform = `translate(${this.mouse.x - 20}px, ${this.mouse.y - 20}px)`;
    this.mainGlow.style.background = `radial-gradient(circle, hsla(${this.hue}, 100%, 65%, ${glowOpacity}) 0%, transparent 70%)`;
    this.mainGlow.style.width = '60px';
    this.mainGlow.style.height = '60px';

    requestAnimationFrame(() => this.animate());
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  new GlowCursor();
});
