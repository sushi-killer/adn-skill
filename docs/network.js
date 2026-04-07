// Amber network background
const canvas = document.getElementById('network-bg');
const ctx = canvas.getContext('2d');
let nodes = [];
let animationStarted = false;

function resize() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}
resize();
window.addEventListener('resize', resize);

// Delay spawning nodes to avoid corner flash
setTimeout(() => {
  for (let i = 0; i < 40; i++) {
    nodes.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      r: Math.random() * 2 + 1.5
    });
  }
  animationStarted = true;
}, 500); // 500ms delay before spawning nodes

function draw() {
  ctx.fillStyle = 'rgba(10, 8, 0, 0.05)';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const dx = nodes[i].x - nodes[j].x;
      const dy = nodes[i].y - nodes[j].y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 180) {
        ctx.beginPath();
        ctx.strokeStyle = `rgba(255, 176, 0, ${(1 - dist / 180) * 0.6})`;
        ctx.lineWidth = 0.5;
        ctx.moveTo(nodes[i].x, nodes[i].y);
        ctx.lineTo(nodes[j].x, nodes[j].y);
        ctx.stroke();
      }
    }
  }

  nodes.forEach(n => {
    ctx.beginPath();
    ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255, 176, 0, 0.8)';
    ctx.fill();
    n.x += n.vx;
    n.y += n.vy;
    if (n.x < 0 || n.x > canvas.width) n.vx *= -1;
    if (n.y < 0 || n.y > canvas.height) n.vy *= -1;
  });

  requestAnimationFrame(draw);
}
draw();
