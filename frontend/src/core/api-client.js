import { APP_CONFIG } from './config.js';

export async function getJson(url, options = {}) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(
    () => controller.abort(),
    options.timeoutMs ?? APP_CONFIG.requestTimeoutMs,
  );

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`Yêu cầu thất bại với mã ${response.status}.`);
    }

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
