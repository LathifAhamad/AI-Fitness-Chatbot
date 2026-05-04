// ============================================================
// PARTICLE SYSTEM — Interactive canvas-based floating particles
// ============================================================

class ParticleSystem {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    this.particles = [];
    this.mouse = { x: -1000, y: -1000 };
    this.particleCount = 90;
    this.connectionDistance = 150;
    this.mouseRadius = 200;
    this.colors = [
      'rgba(0, 240, 255,',   // cyan
      'rgba(255, 0, 110,',   // magenta
      'rgba(57, 255, 20,',   // lime
      'rgba(138, 43, 226,',  // violet
      'rgba(255, 165, 0,',   // orange
    ];
    this.animationId = null;
    this.init();
  }

  init() {
    this.resize();
    this.createParticles();
    this.addEventListeners();
    this.animate();
  }

  resize() {
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
  }

  createParticles() {
    this.particles = [];
    for (let i = 0; i < this.particleCount; i++) {
      this.particles.push(new Particle(this));
    }
  }

  addEventListeners() {
    window.addEventListener('resize', () => {
      this.resize();
      this.createParticles();
    });

    window.addEventListener('mousemove', (e) => {
      this.mouse.x = e.clientX;
      this.mouse.y = e.clientY;
    });

    window.addEventListener('mouseout', () => {
      this.mouse.x = -1000;
      this.mouse.y = -1000;
    });
  }

  drawConnections() {
    for (let i = 0; i < this.particles.length; i++) {
      for (let j = i + 1; j < this.particles.length; j++) {
        const dx = this.particles[i].x - this.particles[j].x;
        const dy = this.particles[i].y - this.particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < this.connectionDistance) {
          const opacity = (1 - dist / this.connectionDistance) * 0.15;
          this.ctx.beginPath();
          this.ctx.strokeStyle = `rgba(0, 240, 255, ${opacity})`;
          this.ctx.lineWidth = 0.5;
          this.ctx.moveTo(this.particles[i].x, this.particles[i].y);
          this.ctx.lineTo(this.particles[j].x, this.particles[j].y);
          this.ctx.stroke();
        }
      }
    }
  }

  animate() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    this.particles.forEach(p => {
      p.update();
      p.draw();
    });

    this.drawConnections();
    this.animationId = requestAnimationFrame(() => this.animate());
  }
}

class Particle {
  constructor(system) {
    this.system = system;
    this.canvas = system.canvas;
    this.ctx = system.ctx;
    this.x = Math.random() * this.canvas.width;
    this.y = Math.random() * this.canvas.height;
    this.size = Math.random() * 2.5 + 0.5;
    this.baseSize = this.size;
    this.speedX = (Math.random() - 0.5) * 0.8;
    this.speedY = (Math.random() - 0.5) * 0.8;
    this.color = system.colors[Math.floor(Math.random() * system.colors.length)];
    this.opacity = Math.random() * 0.5 + 0.2;
    this.baseOpacity = this.opacity;
    this.pulse = Math.random() * Math.PI * 2;
    this.pulseSpeed = Math.random() * 0.02 + 0.005;
  }

  update() {
    // Pulse effect
    this.pulse += this.pulseSpeed;
    this.opacity = this.baseOpacity + Math.sin(this.pulse) * 0.15;
    this.size = this.baseSize + Math.sin(this.pulse) * 0.5;

    // Mouse interaction
    const dx = this.system.mouse.x - this.x;
    const dy = this.system.mouse.y - this.y;
    const dist = Math.sqrt(dx * dx + dy * dy);

    if (dist < this.system.mouseRadius) {
      const force = (this.system.mouseRadius - dist) / this.system.mouseRadius;
      const angle = Math.atan2(dy, dx);
      // Gentle attraction toward cursor
      this.x += Math.cos(angle) * force * 0.8;
      this.y += Math.sin(angle) * force * 0.8;
      // Glow up near cursor
      this.opacity = Math.min(1, this.baseOpacity + force * 0.5);
      this.size = this.baseSize + force * 2;
    }

    // Movement
    this.x += this.speedX;
    this.y += this.speedY;

    // Wrap around edges
    if (this.x < -10) this.x = this.canvas.width + 10;
    if (this.x > this.canvas.width + 10) this.x = -10;
    if (this.y < -10) this.y = this.canvas.height + 10;
    if (this.y > this.canvas.height + 10) this.y = -10;
  }

  draw() {
    this.ctx.save();
    this.ctx.beginPath();
    this.ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
    this.ctx.fillStyle = `${this.color} ${this.opacity})`;
    this.ctx.fill();

    // Glow effect
    this.ctx.shadowBlur = this.size * 8;
    this.ctx.shadowColor = `${this.color} ${this.opacity * 0.6})`;
    this.ctx.beginPath();
    this.ctx.arc(this.x, this.y, this.size * 0.5, 0, Math.PI * 2);
    this.ctx.fillStyle = `${this.color} ${this.opacity * 0.8})`;
    this.ctx.fill();
    this.ctx.restore();
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  new ParticleSystem('particles-canvas');
});
