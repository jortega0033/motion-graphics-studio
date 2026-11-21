// Scene v1 helpers: cleaning, clamping, layer factories.

export const MAX_LAYERS = 32;

const CTRL = /[\u0000-\u001f\u007f-\u009f]/g;
const CTRL_KEEP_NL = /[\u0000-\u0009\u000b-\u001f\u007f-\u009f]/g;

export const KIND_LABELS = { text: 'Text', rectangle: 'Rectangle', ellipse: 'Ellipse' };

export function uuid() {
  return crypto.randomUUID();
}

export function clampNum(n, min, max) {
  return Math.min(max, Math.max(min, n));
}

// Truncate by code points (the server counts characters, not UTF-16 units).
export function truncate(s, max) {
  const chars = Array.from(s);
  return chars.length > max ? chars.slice(0, max).join('') : s;
}

export function cleanLine(s, max) {
  return truncate(String(s).replace(CTRL, ''), max);
}

export function cleanMultiline(s, max) {
  return truncate(String(s).replace(/\r\n?/g, '\n').replace(CTRL_KEEP_NL, ''), max);
}

export function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

export function bounds(scene) {
  return { xMax: 2 * scene.width, yMax: 2 * scene.height };
}

export function createLayer(kind, scene) {
  const count = scene.layers.filter((l) => l.kind === kind).length + 1;
  const base = {
    id: uuid(),
    kind,
    name: cleanLine(`${KIND_LABELS[kind]} ${count}`, 60),
    x: 0,
    y: 0,
    opacity: 1,
    fill: '#f5a524',
  };
  if (kind === 'rectangle') {
    const width = Math.min(320, scene.width);
    const height = Math.min(180, scene.height);
    return {
      ...base,
      x: Math.round((scene.width - width) / 2),
      y: Math.round((scene.height - height) / 2),
      width,
      height,
    };
  }
  if (kind === 'ellipse') {
    const width = Math.min(260, scene.width);
    const height = Math.min(180, scene.height);
    return {
      ...base,
      x: Math.round((scene.width - width) / 2),
      y: Math.round((scene.height - height) / 2),
      fill: '#5ec2b7',
      width,
      height,
    };
  }
  return {
    ...base,
    x: 80,
    y: 80,
    fill: '#f4f1ea',
    text: 'New text',
    font_size: 64,
    align: 'left',
  };
}

// Deep clone (keeps unknown `tracks`), new id, "<name> copy" clamped to 60 chars.
export function duplicateLayer(layer) {
  const copy = cloneJson(layer);
  copy.id = uuid();
  copy.name = truncate(`${layer.name} copy`, 60);
  return copy;
}
