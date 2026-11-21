import * as api from './api.js';
import { drawScene } from './renderer.js';
import {
  MAX_LAYERS, KIND_LABELS, clampNum, cleanLine, cleanMultiline,
  createLayer, duplicateLayer, uuid,
} from './scene.js';

const $ = (id) => document.getElementById(id);

const S = {
  projectId: null,
  scene: null,
  head: 0,
  selectedId: null,
  state: 'clean', // clean | dirty | saving | failed
  edited: false, // edited while a save was in flight
  attempt: null, // { id, sig } retained for retry of an unchanged draft
  stale: null, // { head, revision } from a stale_head conflict
};

const el = {
  projectsView: $('projects-view'),
  editorView: $('editor-view'),
  canvas: $('stage-canvas'),
  list: $('layer-list'),
};
const ctx = el.canvas.getContext('2d');

// ---------------------------------------------------------------- helpers

function selectedLayer() {
  if (!S.scene) return null;
  return S.scene.layers.find((l) => l.id === S.selectedId) || null;
}

function layerIndex(id) {
  return S.scene.layers.findIndex((l) => l.id === id);
}

function focusLayerButton(id) {
  for (const b of el.list.querySelectorAll('.layer-select')) {
    if (b.dataset.layerId === id) {
      b.focus();
      return true;
    }
  }
  return false;
}

function errorLines(e) {
  const errs = e && e.details && Array.isArray(e.details.errors) ? e.details.errors : [];
  return errs.slice(0, 10).map((x) => `${x.path || ''}: ${x.message || ''}`);
}

function describeError(e) {
  const lines = errorLines(e);
  return [e.message || 'Request failed', ...lines].join('\n');
}

// ---------------------------------------------------------------- views

function showView(name) {
  el.projectsView.hidden = name !== 'projects';
  el.editorView.hidden = name !== 'editor';
}

// ---------------------------------------------------------------- projects view

let createAttempt = null;

async function loadProjects(focusId) {
  $('projects-status').textContent = 'Loading projects…';
  $('projects-error').textContent = '';
  try {
    const projects = await api.listProjects();
    renderProjects(projects);
    $('projects-status').textContent = projects.length
      ? `${projects.length} project${projects.length === 1 ? '' : 's'}`
      : 'No projects yet. Create one above.';
    if (focusId) {
      for (const b of $('project-list').querySelectorAll('.open-project')) {
        if (b.dataset.projectId === focusId) { b.focus(); break; }
      }
    }
  } catch (e) {
    $('projects-status').textContent = 'Could not load projects.';
    $('projects-error').textContent = describeError(e);
  }
}

function renderProjects(projects) {
  const ul = $('project-list');
  ul.replaceChildren();
  for (const p of projects) {
    const li = document.createElement('li');
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'open-project';
    btn.dataset.projectId = p.id;
    btn.textContent = `Open ${p.name}`;
    btn.addEventListener('click', () => openProject(p));
    const meta = document.createElement('span');
    meta.className = 'project-meta';
    meta.textContent = `${p.width}×${p.height} · ${p.duration_frames} frames · revision ${p.head_revision}`;
    li.append(btn, meta);
    ul.append(li);
  }
}

async function openProject(summary) {
  $('projects-error').textContent = '';
  $('projects-status').textContent = 'Opening…';
  try {
    const rev = await api.getRevision(summary.id, summary.head_revision);
    enterEditor(summary.id, rev);
  } catch (e) {
    $('projects-status').textContent = 'Could not open project.';
    $('projects-error').textContent = describeError(e);
  }
}

async function onCreate(ev) {
  ev.preventDefault();
  const nameInput = $('new-project-name');
  const name = cleanLine(nameInput.value, 80).trim();
  const errBox = $('projects-error');
  errBox.textContent = '';
  if (!name) {
    errBox.textContent = 'Enter a project title (1 to 80 characters).';
    nameInput.focus();
    return;
  }
  const payload = { name, template: $('template-select').value, preset: $('preset-select').value };
  const sig = JSON.stringify(payload);
  if (!createAttempt || createAttempt.sig !== sig) createAttempt = { id: uuid(), sig };
  const btn = $('create-project');
  btn.disabled = true;
  $('projects-status').textContent = 'Creating…';
  try {
    const res = await api.createProject({ request_id: createAttempt.id, ...payload });
    createAttempt = null;
    enterEditor(res.project.id, res.revision);
  } catch (e) {
    if (!e.network) createAttempt = null;
    $('projects-status').textContent = 'Could not create project.';
    errBox.textContent = describeError(e);
  } finally {
    btn.disabled = false;
  }
}

// ---------------------------------------------------------------- editor lifecycle

function enterEditor(projectId, revision) {
  S.projectId = projectId;
  S.scene = revision.scene;
  S.head = revision.number;
  S.selectedId = null;
  S.state = 'clean';
  S.edited = false;
  S.attempt = null;
  S.stale = null;
  $('editor-error').textContent = '';
  $('reload-saved').hidden = true;
  showView('editor');
  renderAll();
  $('editor-heading').focus();
}

async function leaveEditor() {
  if (S.state !== 'clean' && !window.confirm('You have unsaved changes. Discard them and go back to projects?')) {
    return;
  }
  const id = S.projectId;
  S.projectId = null;
  S.scene = null;
  S.state = 'clean';
  showView('projects');
  $('projects-status').textContent = '';
  await loadProjects(id);
  if (!document.activeElement || document.activeElement === document.body) $('projects-heading').focus();
}

// ---------------------------------------------------------------- rendering

function renderAll() {
  const sc = S.scene;
  $('scene-title').value = sc.title;
  $('background-color').value = sc.background;
  renderLayers();
  renderInspector();
  drawStage();
  renderControls();
  renderStatus();
}

function drawStage() {
  const sc = S.scene;
  if (el.canvas.width !== sc.width) el.canvas.width = sc.width;
  if (el.canvas.height !== sc.height) el.canvas.height = sc.height;
  drawScene(ctx, sc);
  const n = sc.layers.length;
  el.canvas.setAttribute(
    'aria-label',
    `Preview of ${sc.title}, ${sc.width} by ${sc.height}, ${n} layer${n === 1 ? '' : 's'}`,
  );
}

function renderLayers() {
  el.list.replaceChildren();
  const layers = S.scene.layers;
  for (let i = layers.length - 1; i >= 0; i--) {
    const l = layers[i];
    const li = document.createElement('li');
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'layer-select';
    btn.dataset.layerId = l.id;
    const selected = l.id === S.selectedId;
    btn.setAttribute('aria-pressed', selected ? 'true' : 'false');
    btn.setAttribute('aria-label', `${l.name}, ${KIND_LABELS[l.kind] || l.kind}`);
    const name = document.createElement('span');
    name.className = 'layer-name';
    name.textContent = l.name;
    const kind = document.createElement('span');
    kind.className = 'layer-kind';
    kind.textContent = KIND_LABELS[l.kind] || l.kind;
    btn.append(name, kind);
    if (selected) li.setAttribute('aria-current', 'true');
    li.append(btn);
    el.list.append(li);
  }
  $('layer-empty').hidden = layers.length > 0;
}

const INSPECTOR_FIELDS = [
  'layer-label', 'prop-x', 'prop-y', 'prop-width', 'prop-height', 'prop-opacity',
  'prop-fill', 'prop-text', 'prop-font-size', 'prop-align',
];

function renderInspector() {
  const l = selectedLayer();
  const isText = !!l && l.kind === 'text';
  const isShape = !!l && !isText;
  $('inspector-empty').hidden = !!l;
  $('row-width').hidden = !isShape;
  $('row-height').hidden = !isShape;
  $('row-text').hidden = !isText;
  $('row-font-size').hidden = !isText;
  $('row-align').hidden = !isText;
  for (const id of INSPECTOR_FIELDS) $(id).disabled = !l;
  if (!l) {
    for (const id of INSPECTOR_FIELDS) {
      if (id !== 'prop-fill' && id !== 'prop-align') $(id).value = '';
    }
    return;
  }
  $('layer-label').value = l.name;
  $('prop-x').value = String(l.x);
  $('prop-y').value = String(l.y);
  $('prop-opacity').value = String(l.opacity);
  $('prop-fill').value = l.fill;
  if (isShape) {
    $('prop-width').value = String(l.width);
    $('prop-height').value = String(l.height);
    $('prop-width').max = String(S.scene.width);
    $('prop-height').max = String(S.scene.height);
  } else {
    $('prop-text').value = l.text;
    $('prop-font-size').value = String(l.font_size);
    $('prop-align').value = l.align;
  }
}

function renderControls() {
  const l = selectedLayer();
  const layers = S.scene.layers;
  const idx = l ? layerIndex(l.id) : -1;
  const full = layers.length >= MAX_LAYERS;
  $('move-up').disabled = !l || idx === layers.length - 1;
  $('move-down').disabled = !l || idx === 0;
  $('duplicate-layer').disabled = !l || full;
  $('delete-layer').disabled = !l;
  for (const id of ['add-text-layer', 'add-rectangle-layer', 'add-ellipse-layer']) $(id).disabled = full;
  // Stays enabled so keyboard focus is never stranded; save() ignores clean and in-flight states.
  $('save-button').setAttribute('aria-disabled', S.state === 'saving' || S.state === 'clean' ? 'true' : 'false');
}

function renderStatus() {
  const text = {
    clean: `Saved · revision ${S.head}`,
    dirty: 'Unsaved changes',
    saving: 'Saving…',
    failed: 'Save failed',
  }[S.state];
  $('save-status').textContent = text;
}

// ---------------------------------------------------------------- mutation

function touch() {
  if (S.state === 'saving') S.edited = true;
  else S.state = 'dirty';
}

// opts: { list, inspector }
function changed(opts = {}) {
  touch();
  if (opts.list) renderLayers();
  if (opts.inspector) renderInspector();
  drawStage();
  renderControls();
  renderStatus();
}

function selectLayer(id, focus) {
  S.selectedId = id;
  renderLayers();
  renderInspector();
  renderControls();
  if (focus) focusLayerButton(id);
}

function addLayer(kind) {
  if (S.scene.layers.length >= MAX_LAYERS) return;
  const layer = createLayer(kind, S.scene);
  S.scene.layers.push(layer);
  S.selectedId = layer.id;
  changed({ list: true, inspector: true });
}

function moveLayer(id, delta) {
  const i = layerIndex(id);
  const j = i + delta;
  if (i < 0 || j < 0 || j >= S.scene.layers.length) return;
  const arr = S.scene.layers;
  [arr[i], arr[j]] = [arr[j], arr[i]];
  S.selectedId = id;
  changed({ list: true, inspector: true });
  focusLayerButton(id);
}

function duplicateSelected(id) {
  const i = layerIndex(id);
  if (i < 0 || S.scene.layers.length >= MAX_LAYERS) return;
  const copy = duplicateLayer(S.scene.layers[i]);
  S.scene.layers.splice(i + 1, 0, copy);
  S.selectedId = copy.id;
  changed({ list: true, inspector: true });
  focusLayerButton(copy.id);
}

function deleteLayer(id) {
  const i = layerIndex(id);
  if (i < 0) return;
  S.scene.layers.splice(i, 1);
  const arr = S.scene.layers;
  const next = arr.length ? arr[Math.max(0, i - 1)] : null;
  S.selectedId = next ? next.id : null;
  changed({ list: true, inspector: true });
  if (next) focusLayerButton(next.id);
  else $('add-text-layer').focus();
}

// ---------------------------------------------------------------- inspector bindings

// Numeric field: apply clamped value while typing, normalise display on change.
function bindNumber(id, apply) {
  const input = $(id);
  input.addEventListener('input', () => {
    const l = selectedLayer();
    if (!l || input.value.trim() === '') return;
    const n = Number(input.value);
    if (!Number.isFinite(n)) return;
    apply(l, n);
    changed();
  });
  input.addEventListener('change', () => {
    renderInspector();
  });
}

function bindInspector() {
  bindNumber('prop-x', (l, n) => { l.x = clampNum(n, -2 * S.scene.width, 2 * S.scene.width); });
  bindNumber('prop-y', (l, n) => { l.y = clampNum(n, -2 * S.scene.height, 2 * S.scene.height); });
  bindNumber('prop-opacity', (l, n) => { l.opacity = clampNum(n, 0, 1); });
  bindNumber('prop-width', (l, n) => {
    if (l.kind !== 'text') l.width = clampNum(n, 1, S.scene.width);
  });
  bindNumber('prop-height', (l, n) => {
    if (l.kind !== 'text') l.height = clampNum(n, 1, S.scene.height);
  });
  bindNumber('prop-font-size', (l, n) => {
    if (l.kind === 'text') l.font_size = clampNum(n, 8, 192);
  });

  $('prop-fill').addEventListener('input', () => {
    const l = selectedLayer();
    if (!l) return;
    l.fill = $('prop-fill').value.toLowerCase();
    changed();
  });

  $('prop-align').addEventListener('change', () => {
    const l = selectedLayer();
    if (!l || l.kind !== 'text') return;
    l.align = $('prop-align').value;
    changed();
  });

  const text = $('prop-text');
  text.addEventListener('input', () => {
    const l = selectedLayer();
    if (!l || l.kind !== 'text') return;
    const v = cleanMultiline(text.value, 256);
    if (v === '') return;
    l.text = v;
    changed();
  });
  text.addEventListener('change', () => renderInspector());

  const label = $('layer-label');
  label.addEventListener('input', () => {
    const l = selectedLayer();
    if (!l) return;
    const v = cleanLine(label.value, 60);
    if (v.trim() === '') return;
    l.name = v;
    changed({ list: true });
  });
  label.addEventListener('change', () => renderInspector());

  const title = $('scene-title');
  title.addEventListener('input', () => {
    const v = cleanLine(title.value, 80);
    if (v.trim() === '') return;
    S.scene.title = v;
    changed();
  });
  title.addEventListener('change', () => { title.value = S.scene.title; });

  $('background-color').addEventListener('input', () => {
    S.scene.background = $('background-color').value.toLowerCase();
    changed();
  });
}

// ---------------------------------------------------------------- saving

async function save() {
  if (!S.scene || S.state === 'saving' || S.state === 'clean') return;
  const projectId = S.projectId;
  const body = { expected_head: S.head, scene: S.scene };
  const sig = JSON.stringify(body);
  if (!S.attempt || S.attempt.sig !== sig) {
    const id = uuid();
    // Serialise once: a retry of this attempt resends exactly these bytes under the same request id.
    S.attempt = { id, sig, payload: JSON.stringify({ request_id: id, ...body }) };
  }
  const payload = S.attempt.payload;
  S.state = 'saving';
  S.edited = false;
  $('editor-error').textContent = '';
  $('reload-saved').hidden = true;
  S.stale = null;
  renderControls();
  renderStatus();
  try {
    const res = await api.saveRevision(projectId, payload);
    if (S.projectId !== projectId) return;
    S.head = res.revision.number;
    S.attempt = null;
    S.state = S.edited ? 'dirty' : 'clean';
  } catch (e) {
    if (S.projectId !== projectId) return;
    S.state = S.edited ? 'dirty' : 'failed';
    if (e.network) {
      $('editor-error').textContent =
        'Could not reach the server. Your draft is still here. Save again to retry.';
    } else {
      S.attempt = null;
      if (e.status === 409 && e.code === 'stale_head') {
        const head = e.details && e.details.current_head;
        S.stale = { head, revision: e.details && e.details.current_revision };
        $('editor-error').textContent = `Another tab saved revision ${head}. Your draft is still here.`;
        $('reload-saved').hidden = false;
      } else if (e.status === 422) {
        $('editor-error').textContent = describeError(e);
      } else {
        $('editor-error').textContent = describeError(e);
      }
      if (S.state === 'dirty') S.state = 'failed';
    }
    if (S.edited) S.state = 'dirty';
  }
  S.edited = false;
  renderControls();
  renderStatus();
}

async function reloadSaved() {
  if (!S.stale) return;
  if (!window.confirm('Discard your draft and load the saved version?')) return;
  let rev = S.stale.revision;
  try {
    if (!rev || !rev.scene) rev = await api.getRevision(S.projectId, S.stale.head);
  } catch (e) {
    $('editor-error').textContent = describeError(e);
    return;
  }
  const keep = S.selectedId;
  S.scene = rev.scene;
  S.head = rev.number;
  S.state = 'clean';
  S.edited = false;
  S.attempt = null;
  S.stale = null;
  S.selectedId = S.scene.layers.some((l) => l.id === keep) ? keep : null;
  $('editor-error').textContent = '';
  $('reload-saved').hidden = true;
  renderAll();
  $('save-button').focus();
}

// ---------------------------------------------------------------- wiring

function bindEvents() {
  $('create-form').addEventListener('submit', onCreate);
  $('back-to-projects').addEventListener('click', leaveEditor);
  $('save-button').addEventListener('click', save);
  $('reload-saved').addEventListener('click', reloadSaved);

  $('add-text-layer').addEventListener('click', () => addLayer('text'));
  $('add-rectangle-layer').addEventListener('click', () => addLayer('rectangle'));
  $('add-ellipse-layer').addEventListener('click', () => addLayer('ellipse'));

  $('move-up').addEventListener('click', () => S.selectedId && moveLayer(S.selectedId, 1));
  $('move-down').addEventListener('click', () => S.selectedId && moveLayer(S.selectedId, -1));
  $('duplicate-layer').addEventListener('click', () => S.selectedId && duplicateSelected(S.selectedId));
  $('delete-layer').addEventListener('click', () => S.selectedId && deleteLayer(S.selectedId));

  el.list.addEventListener('click', (ev) => {
    const btn = ev.target.closest('.layer-select');
    if (btn) selectLayer(btn.dataset.layerId, true);
  });

  el.list.addEventListener('keydown', (ev) => {
    const btn = ev.target.closest('.layer-select');
    if (!btn) return;
    const id = btn.dataset.layerId;
    if (ev.key === 'Delete' && !ev.altKey && !ev.ctrlKey && !ev.metaKey) {
      ev.preventDefault();
      deleteLayer(id);
    } else if (ev.altKey && (ev.key === 'ArrowUp' || ev.key === 'ArrowDown')) {
      ev.preventDefault();
      moveLayer(id, ev.key === 'ArrowUp' ? 1 : -1);
    }
  });

  document.addEventListener('keydown', (ev) => {
    if ((ev.ctrlKey || ev.metaKey) && !ev.altKey && ev.key.toLowerCase() === 's') {
      ev.preventDefault();
      if (!el.editorView.hidden) save();
    }
  });

  window.addEventListener('beforeunload', (ev) => {
    if (!el.editorView.hidden && S.state !== 'clean') {
      ev.preventDefault();
      ev.returnValue = '';
    }
  });

  bindInspector();
}

async function init() {
  bindEvents();
  showView('projects');
  api.refreshToken().catch(() => { /* retried lazily on first write */ });
  await loadProjects();
}

init();
