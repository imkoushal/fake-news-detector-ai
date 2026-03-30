const STORAGE_KEY = "analysis_history";

export function getHistory() {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

export function addToHistory(item) {
  const history = getHistory();
  history.unshift({
    ...item,
    timestamp: new Date().toISOString(),
  });
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
}

export function clearHistory() {
  localStorage.removeItem(STORAGE_KEY);
}
