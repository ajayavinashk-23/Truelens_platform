/**
 * Thin client for the FastAPI forensics inference backend.
 *
 * Requests go to relative /api/* paths, which the Vite dev server proxies
 * to http://localhost:8000 (see vite.config.js). This means no CORS
 * headaches in dev, and only one line to change (the proxy target) if the
 * backend ever moves.
 */

const ENDPOINTS = {
  image: "/api/image/analyze",
  video: "/api/video/analyze",
  audio: "/api/audio/analyze",
};

/**
 * Thrown only when the backend genuinely could not be reached at all
 * (server not running, DNS/connection failure, CORS block before any
 * response is received). This is the ONLY case that should trigger the
 * demo/mock fallback in Dashboard.jsx — a request that reached the server
 * and came back with an error status is a real bug, not "no backend", and
 * must never be silently replaced with a randomized demo report (doing so
 * is what caused the same image to appear to get a different verdict on
 * every retry).
 */
export class BackendUnreachableError extends Error {
  constructor(message) {
    super(message);
    this.name = "BackendUnreachableError";
  }
}

/**
 * Sends a file to the matching pretrained-model inference endpoint and
 * returns the parsed forensics report JSON (same shape the dashboard
 * already renders from the mock generator).
 *
 * @param {"image"|"video"|"audio"} mediaType
 * @param {File} file
 * @returns {Promise<object>} forensics report JSON
 */
export async function analyzeMedia(mediaType, file) {
  const endpoint = ENDPOINTS[mediaType];
  if (!endpoint) {
    throw new Error(`Unsupported media type: ${mediaType}`);
  }
  if (!file) {
    throw new Error("No file provided for analysis.");
  }

  const formData = new FormData();
  formData.append("file", file);

  let response;
  try {
    response = await fetch(endpoint, { method: "POST", body: formData });
  } catch (networkErr) {
    // Backend not running / unreachable — let the caller decide how to
    // degrade (e.g. fall back to a clearly-labeled demo report). This is
    // the ONLY failure mode that should ever be treated as "no backend".
    throw new BackendUnreachableError(
      `Could not reach the forensics backend at ${endpoint}. Is the FastAPI server running? (${networkErr.message})`
    );
  }

  if (!response.ok) {
    let detail = response.statusText;
    let gotJsonBody = false;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
      gotJsonBody = true;
    } catch {
      // Response wasn't JSON at all — this isn't FastAPI's own error
      // handler talking back, it's something else answering at that URL
      // (a dev-server 404 page, a misconfigured proxy, a load balancer
      // error page, etc). That means there's effectively no real backend
      // to analyze with, same as a network failure — treat it the same
      // way so it degrades to the demo report instead of showing a
      // confusing raw HTTP-status error.
    }
    if (!gotJsonBody) {
      throw new BackendUnreachableError(
        `The forensics backend at ${endpoint} did not return a valid response (HTTP ${response.status}). Is the FastAPI server running and is the dev-server proxy pointed at it?`
      );
    }
    // The server was reached AND answered with FastAPI's own JSON error
    // shape — this is a real inference/validation error (bad file, model
    // exception, etc.), not "backend unreachable". It must surface as a
    // genuine error, not be silently swapped for a randomized demo report.
    throw new Error(`Analysis failed (${response.status}): ${detail}`);
  }

  return response.json();
}
