// Canvas2D renderer for scene v1. A future sampler can pass `frame` as a third argument.

export function drawScene(ctx, scene /*, frame */) {
  ctx.save();
  ctx.globalAlpha = 1;
  ctx.fillStyle = scene.background;
  ctx.fillRect(0, 0, scene.width, scene.height);
  ctx.restore();

  for (const layer of scene.layers) {
    ctx.save();
    ctx.globalAlpha = layer.opacity;
    ctx.fillStyle = layer.fill;
    if (layer.kind === 'rectangle') {
      ctx.fillRect(layer.x, layer.y, layer.width, layer.height);
    } else if (layer.kind === 'ellipse') {
      ctx.beginPath();
      ctx.ellipse(
        layer.x + layer.width / 2,
        layer.y + layer.height / 2,
        layer.width / 2,
        layer.height / 2,
        0, 0, Math.PI * 2,
      );
      ctx.fill();
    } else if (layer.kind === 'text') {
      ctx.textBaseline = 'top';
      ctx.font = `${layer.font_size}px sans-serif`;
      ctx.textAlign = layer.align;
      const lineHeight = layer.font_size * 1.2;
      const lines = String(layer.text).split('\n');
      for (let i = 0; i < lines.length; i++) {
        ctx.fillText(lines[i], layer.x, layer.y + i * lineHeight);
      }
    }
    ctx.restore();
  }
}
