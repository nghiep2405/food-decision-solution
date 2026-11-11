import { APP_CONFIG } from './config.js';

function resolveUrl(url) {
  if (typeof url === 'string' && url.startsWith('/api/')) {
    return `${APP_CONFIG.apiBaseUrl.replace(/\/$/, '')}${url}`;
  }
  return url;
}

export async function requestJson(url, options = {}) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(
    () => controller.abort(),
    options.timeoutMs ?? APP_CONFIG.requestTimeoutMs,
  );

  try {
    const response = await fetch(resolveUrl(url), {
      method: options.method ?? 'GET',
      headers: {
        Accept: 'application/json',
        ...(options.headers ?? {}),
      },
      body: options.body,
      signal: controller.signal,
    });

    if (!response.ok) {
      let detail = null;
      try {
        const payload = await response.json();
        detail = typeof payload?.detail === 'string' ? payload.detail : null;
      } catch {
        // The status code remains useful when the server does not return JSON.
      }
      throw new Error(detail ?? `Yêu cầu thất bại với mã ${response.status}.`);
    }

    if (response.status === 204) return null;
    return await response.json();
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('Yêu cầu dữ liệu đã quá thời gian chờ.');
    }

    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export function getJson(url, options = {}) {
  return requestJson(url, { ...options, method: 'GET' });
}

export function postJson(url, payload, options = {}) {
  return requestJson(url, {
    ...options,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
    body: JSON.stringify(payload),
  });
}

export function uploadForm(url, formData, options = {}) {
  return requestJson(url, {
    ...options,
    method: 'POST',
    body: formData,
  });
}
