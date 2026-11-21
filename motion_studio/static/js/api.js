// Thin fetch wrapper for the Motion Studio API with session-token handling.

let token = null;

export class ApiError extends Error {
  constructor({ status = 0, code = 'error', message = 'Request failed', details = {}, network = false }) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details || {};
    this.network = network;
  }
}

async function readJson(res) {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

function toError(res, data) {
  const err = data && data.error ? data.error : {};
  return new ApiError({
    status: res.status,
    code: err.code || 'http_' + res.status,
    message: err.message || `Request failed (HTTP ${res.status})`,
    details: err.details || {},
  });
}

function networkError() {
  return new ApiError({
    network: true,
    code: 'network_error',
    message: 'Could not reach the server.',
  });
}

export async function refreshToken() {
  let res;
  try {
    res = await fetch('/api/session', { cache: 'no-store', headers: { Accept: 'application/json' } });
  } catch {
    throw networkError();
  }
  const data = await readJson(res);
  if (!res.ok || !data || typeof data.token !== 'string') throw toError(res, data);
  token = data.token;
  return token;
}

async function request(method, path, body) {
  const write = method !== 'GET';
  for (let attempt = 0; attempt < 2; attempt++) {
    const headers = { Accept: 'application/json' };
    const opts = { method, headers, cache: 'no-store' };
    if (write) {
      if (!token) await refreshToken();
      headers['Content-Type'] = 'application/json';
      headers['X-Session-Token'] = token;
      // A pre-serialised string is sent unchanged so a retried request id always matches its bytes.
      opts.body = typeof body === 'string' ? body : JSON.stringify(body === undefined ? {} : body);
    }
    let res;
    try {
      res = await fetch(path, opts);
    } catch {
      throw networkError();
    }
    const data = await readJson(res);
    if (res.ok) return data;
    const err = toError(res, data);
    if (write && attempt === 0 && err.code === 'session_invalid') {
      await refreshToken();
      continue;
    }
    throw err;
  }
  throw new ApiError({ message: 'Request failed' });
}

export const get = (path) => request('GET', path);
export const post = (path, body) => request('POST', path, body);

export async function listProjects() {
  const data = await get('/api/projects');
  return Array.isArray(data.projects) ? data.projects : [];
}

export async function createProject(payload) {
  return post('/api/projects', payload);
}

export async function getRevision(projectId, number) {
  const data = await get(`/api/projects/${encodeURIComponent(projectId)}/revisions/${encodeURIComponent(number)}`);
  return data.revision;
}

export async function saveRevision(projectId, payload) {
  return post(`/api/projects/${encodeURIComponent(projectId)}/revisions`, payload);
}
