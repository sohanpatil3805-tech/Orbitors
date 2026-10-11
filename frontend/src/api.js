import { useCallback, useEffect, useState } from 'react';

// Vite proxies /api to the FastAPI backend (vite.config.js). Set VITE_API_BASE to call another host.
const API_BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export async function api(path, { method = 'GET', body, signal } = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      signal,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    if (e.name === 'AbortError') throw e;
    throw new ApiError('Backend unreachable — start it with: cd backend && python run.py', 0);
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : JSON.stringify(data?.detail ?? `HTTP ${res.status}`);
    throw new ApiError(detail, res.status);
  }
  return data;
}

/**
 * Fetch `path` (re-fetching every `intervalMs` when given). `path = null` skips the request.
 * Returns { data, error, loading, reload }; the last good data is kept when a refresh fails.
 */
export function useApi(path, { intervalMs = 0 } = {}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(Boolean(path));
  const [tick, setTick] = useState(0);
  const [lastPath, setLastPath] = useState(path);

  if (lastPath !== path) {   // new request: drop the previous result (React's "adjust state on prop change")
    setLastPath(path);
    setData(null);
    setError(null);
    setLoading(Boolean(path));
  }

  useEffect(() => {
    if (!path) return undefined;
    const ctrl = new AbortController();
    api(path, { signal: ctrl.signal })
      .then((d) => { setData(d); setError(null); })
      .catch((e) => { if (e.name !== 'AbortError') setError(e); })
      .finally(() => { if (!ctrl.signal.aborted) setLoading(false); });
    return () => ctrl.abort();
  }, [path, tick]);

  useEffect(() => {
    if (!path || !intervalMs) return undefined;
    const id = setInterval(() => setTick((t) => t + 1), intervalMs);
    return () => clearInterval(id);
  }, [path, intervalMs]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload };
}
