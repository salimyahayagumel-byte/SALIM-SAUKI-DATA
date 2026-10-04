const statusElement = document.querySelector<HTMLElement>("#v8-status");
const resultElement = document.querySelector<HTMLElement>("#v8-result");
const scanButton = document.querySelector<HTMLButtonElement>("#v8-scan");
const queryInput = document.querySelector<HTMLInputElement>("#v8-query");

function setStatus(message: string): void {
  if (statusElement) statusElement.textContent = message;
}

async function checkHealth(): Promise<void> {
  try {
    const response = await fetch("/api/v8/health");
    const data = await response.json() as { success?: boolean; version?: string };
    setStatus(data.success ? `🟢 V8 API ${data.version ?? "ready"}` : "🔴 V8 API error");
  } catch {
    setStatus("🔴 V8 API unavailable");
  }
}

async function runScan(): Promise<void> {
  const query = queryInput?.value.trim() || "sol";
  if (scanButton) scanButton.disabled = true;
  setStatus("🔎 Scanning...");
  try {
    const response = await fetch(`/api/v8/scan?query=${encodeURIComponent(query)}`);
    const data = await response.json() as unknown;
    if (resultElement) {
      resultElement.textContent = JSON.stringify(data, null, 2);
    }
    setStatus(response.ok ? "🟢 Scan complete" : "🟠 Scan returned an error");
  } catch (error) {
    if (resultElement) resultElement.textContent = String(error);
    setStatus("🔴 Scan failed");
  } finally {
    if (scanButton) scanButton.disabled = false;
  }
}

scanButton?.addEventListener("click", () => void runScan());
void checkHealth();
