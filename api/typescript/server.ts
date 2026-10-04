import { createServer, IncomingMessage, ServerResponse } from "node:http";
import { URL } from "node:url";

const HOST = process.env.TS_API_HOST ?? "0.0.0.0";
const PORT = Number(process.env.TS_API_PORT ?? "8787");
const PYTHON_DASHBOARD = process.env.PYTHON_DASHBOARD_URL ?? "http://127.0.0.1:8000";

function send(res: ServerResponse, status: number, data: unknown): void {
  const body = JSON.stringify(data);
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Cache-Control", "no-store");
  res.end(body);
}

async function proxy(path: string): Promise<unknown> {
  const response = await fetch(`${PYTHON_DASHBOARD}${path}`);
  const text = await response.text();
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    data = { raw: text };
  }
  if (!response.ok) {
    throw new Error(`Python dashboard returned HTTP ${response.status}`);
  }
  return data;
}

async function handler(req: IncomingMessage, res: ServerResponse): Promise<void> {
  const url = new URL(req.url ?? "/", `http://${req.headers.host ?? "localhost"}`);

  if (req.method === "OPTIONS") {
    res.statusCode = 204;
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET,OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    res.end();
    return;
  }

  if (req.method !== "GET") {
    send(res, 405, { success: false, error: "Method not allowed" });
    return;
  }

  if (url.pathname === "/api/v8/health") {
    send(res, 200, {
      success: true,
      service: "SALIM SAUKI DATA TypeScript API",
      version: "V8",
      runtime: "Node.js + TypeScript",
      pythonDashboard: PYTHON_DASHBOARD,
    });
    return;
  }

  if (url.pathname === "/api/v8/dashboard/health") {
    try {
      send(res, 200, await proxy("/health"));
    } catch (error) {
      send(res, 503, {
        success: false,
        error: error instanceof Error ? error.message : String(error),
      });
    }
    return;
  }

  if (url.pathname === "/api/v8/scan") {
    const query = (url.searchParams.get("query") ?? "sol").trim() || "sol";
    try {
      send(res, 200, await proxy(`/api/scan?query=${encodeURIComponent(query)}`));
    } catch (error) {
      send(res, 503, {
        success: false,
        error: error instanceof Error ? error.message : String(error),
      });
    }
    return;
  }

  send(res, 404, {
    success: false,
    error: "V8 API route not found",
    routes: ["/api/v8/health", "/api/v8/dashboard/health", "/api/v8/scan?query=sol"],
  });
}

createServer((req, res) => {
  void handler(req, res).catch((error) => {
    send(res, 500, {
      success: false,
      error: error instanceof Error ? error.message : String(error),
    });
  });
}).listen(PORT, HOST, () => {
  console.log("========================================");
  console.log("SALIM SAUKI DATA V8 TypeScript API");
  console.log("========================================");
  console.log(`Listening: http://${HOST}:${PORT}`);
  console.log(`Python dashboard: ${PYTHON_DASHBOARD}`);
});
