const STORAGE_KEY = "truelens.detection_history";
const MAX_ENTRIES = 25;

/** @returns {Array} stored history, most recent first */
export function getHistory() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

/**
 * Prepend a completed report to history and persist it.
 * @param {object} report - result of generateMockReport / future API response
 */
export function addToHistory(report) {
  try {
    const history = getHistory();
    const entry = {
      id: `${Date.now()}`,
      file_name: report.file_name,
      media_type: report.media_type,
      prediction: report.prediction,
      deepfake_probability: report.deepfake_probability,
      risk_level: report.risk_level,
      timestamp: report.timestamp,
    };
    const updated = [entry, ...history].slice(0, MAX_ENTRIES);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    return updated;
  } catch {
    return getHistory();
  }
}

export function clearHistory() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* no-op */
  }
}
