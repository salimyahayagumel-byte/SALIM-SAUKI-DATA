const state = {
    signals: [],
    chain: "all",
    search: ""
};

const $ = (selector) => document.querySelector(selector);

async function loadSignals() {
    try {
        const response = await fetch(`/api/signals?limit=100&chain=${encodeURIComponent(state.chain)}`, {
            cache: "no-store",
            headers: { "Accept": "application/json" }
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const payload = await response.json();
        state.signals = Array.isArray(payload.signals) ? payload.signals : [];
        render();
        const stamp = payload.updated_at ? new Date(payload.updated_at) : new Date();
        $("#lastUpdate").textContent = stamp.toLocaleTimeString();
    } catch (error) {
        console.error("Signal feed error:", error);
        $("#lastUpdate").textContent = "OFFLINE";
    }
}

function money(value) {
    const n = Number(value || 0);
    if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
    if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
    if (n >= 1e3) return `$${(n / 1e3).toFixed(1)}K`;
    return `$${n.toFixed(0)}`;
}

function number(value) {
    return Number(value || 0).toLocaleString();
}

function score(value) {
    return Math.max(0, Math.min(100, Number(value || 0)));
}

function chainLabel(chain) {
    return ({
        solana: "Solana",
        base: "Base",
        robinhood: "Robinhood",
        arc: "Arc"
    })[String(chain || "").toLowerCase()] || String(chain || "Unknown").toUpperCase();
}

function chainClass(chain) {
    return `chain-${String(chain || "unknown").toLowerCase()}`;
}

function signalClass(signal) {
    const value = String(signal || "").toUpperCase();
    if (value.includes("STRONG")) return "strong";
    if (value.includes("GEM SIGNAL")) return "gem";
    return "early";
}

function safeUrl(value) {
    const text = String(value || "").trim();
    if (!text) return "#";
    try {
        const url = new URL(text, window.location.origin);
        if (!["http:", "https:"].includes(url.protocol)) return "#";
        return url.href;
    } catch {
        return "#";
    }
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function explorerUrl(token) {
    if (token.explorer_url) return token.explorer_url;
    const address = encodeURIComponent(token.address || "");
    const chain = String(token.chain || "").toLowerCase();
    if (chain === "solana") return `https://solscan.io/token/${address}`;
    if (chain === "base") return `https://basescan.org/token/${address}`;
    return "#";
}

function scoreBar(label, value) {
    const n = score(value);
    return `<div class="score-line"><span>${label}</span><strong>${n}/100</strong></div><div class="score-track"><div style="width:${n}%"></div></div>`;
}

function filteredSignals() {
    const query = state.search.toLowerCase();
    return state.signals.filter(token => {
        if (state.chain !== "all" && String(token.chain || "").toLowerCase() !== state.chain) return false;
        if (!query) return true;
        return [token.symbol, token.name, token.address, token.chain]
            .some(value => String(value || "").toLowerCase().includes(query));
    });
}

function render() {
    const signals = filteredSignals();
    const totalVolume = signals.reduce((sum, t) => sum + Number(t.volume24h || 0), 0);
    const topScore = signals.reduce((max, t) => Math.max(max, score(t.final_score)), 0);
    const gemCount = signals.filter(t => String(t.final_status || "").toUpperCase() !== "EARLY GEM").length;

    $("#signalCount").textContent = number(signals.length);
    $("#gemCount").textContent = number(gemCount);
    $("#volume").textContent = money(totalVolume);
    $("#topScore").textContent = topScore;
    $("#feedCount").textContent = `${signals.length} signal${signals.length === 1 ? "" : "s"}`;

    const grid = $("#signalGrid");
    if (!signals.length) {
        grid.innerHTML = `<div class="empty-state"><div class="empty-icon">🔎</div><h3>No matching signals</h3><p>The live feed has no signal matching the current filter.</p></div>`;
        return;
    }
    grid.innerHTML = signals.map(tokenCard).join("");
}

function tokenCard(token) {
    const symbol = escapeHtml(token.symbol || "N/A");
    const name = escapeHtml(token.name || "Unknown Token");
    const signal = escapeHtml(token.final_signal || token.final_status || "SIGNAL");
    const chain = String(token.chain || "unknown").toLowerCase();
    const logo = safeUrl(token.image_url || "");
    const image = logo !== "#" ? `<img src="${escapeHtml(logo)}" alt="${symbol}" loading="lazy" onerror="this.style.display='none'">` : `<div class="token-logo-fallback">$</div>`;
    const sentAt = token.sent_at ? new Date(Number(token.sent_at) * 1000) : null;
    const age = token.pair_age_seconds ? formatAge(Number(token.pair_age_seconds)) : "—";
    const buy = Number(token.buy_ratio || 0) * 100;
    const sell = Math.max(0, 100 - buy);
    const address = String(token.address || "");

    return `<article class="signal-card ${chainClass(chain)}" data-address="${escapeHtml(address)}">
        <div class="card-top">
            <div class="token-title">
                <div class="logo-wrap">${image}</div>
                <div><div class="symbol">$${symbol}</div><div class="name">${name}</div></div>
            </div>
            <span class="signal-badge ${signalClass(signal)}">${signal}</span>
        </div>

        <div class="chain-row"><span>⛓️ ${escapeHtml(chainLabel(chain))}</span><span>${sentAt ? escapeHtml(sentAt.toLocaleString()) : ""}</span></div>

        <div class="market-grid">
            <div><span>MC</span><strong>${money(token.marketcap)}</strong></div>
            <div><span>LIQ</span><strong>${money(token.liquidity)}</strong></div>
            <div><span>VOL 24H</span><strong>${money(token.volume24h)}</strong></div>
            <div><span>TXNS</span><strong>${number(token.total_txns || token.txns1h)}</strong></div>
        </div>

        <div class="flow-row"><span>🟢 BUY ${buy.toFixed(1)}%</span><span>🔴 SELL ${sell.toFixed(1)}%</span><span>🕒 ${escapeHtml(age)}</span></div>

        <div class="scores-card">
            ${scoreBar("🤖 AI", token.ai_score)}
            ${scoreBar("💎 GEM", token.gem_score)}
            ${scoreBar("🛡️ SECURITY", token.security_score)}
            ${scoreBar("🎯 FINAL", token.final_score)}
        </div>

        <div class="card-links">
            <a href="${escapeHtml(safeUrl(token.url))}" target="_blank" rel="noopener noreferrer">📊 Chart</a>
            <a href="${escapeHtml(safeUrl(explorerUrl(token)))}" target="_blank" rel="noopener noreferrer">🔍 Explorer</a>
            ${token.website_url ? `<a href="${escapeHtml(safeUrl(token.website_url))}" target="_blank" rel="noopener noreferrer">🌐 Web</a>` : ""}
            ${token.twitter_url ? `<a href="${escapeHtml(safeUrl(token.twitter_url))}" target="_blank" rel="noopener noreferrer">𝕏 X</a>` : ""}
            ${token.telegram_url ? `<a href="${escapeHtml(safeUrl(token.telegram_url))}" target="_blank" rel="noopener noreferrer">✈️ TG</a>` : ""}
        </div>

        <button class="detail-button" type="button" onclick="openDetail('${escapeHtml(address)}')">VIEW TOKEN →</button>
    </article>`;
}

function formatAge(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) return "—";
    if (seconds < 60) return `${Math.floor(seconds)}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
    return `${Math.floor(seconds / 86400)}d`;
}

function openDetail(address) {
    const token = state.signals.find(t => String(t.address || "") === address);
    if (!token) return;
    const chain = String(token.chain || "").toLowerCase();
    const securityMin = chain === "solana" ? 90 : 69;
    const website = token.website_url ? `<a href="${escapeHtml(safeUrl(token.website_url))}" target="_blank" rel="noopener noreferrer">Website</a>` : "";
    const x = token.twitter_url ? `<a href="${escapeHtml(safeUrl(token.twitter_url))}" target="_blank" rel="noopener noreferrer">X</a>` : "";
    const tg = token.telegram_url ? `<a href="${escapeHtml(safeUrl(token.telegram_url))}" target="_blank" rel="noopener noreferrer">Telegram</a>` : "";

    $("#modalContent").innerHTML = `<div class="detail-head">
        <div class="eyebrow">${escapeHtml(chainLabel(chain))} · SIGNAL DETAIL</div>
        <h2>$${escapeHtml(token.symbol || "N/A")} <span>${escapeHtml(token.name || "")}</span></h2>
        <div class="detail-address">${escapeHtml(token.address || "")}</div>
    </div>
    <div class="detail-stats">
        <div><span>Market Cap</span><strong>${money(token.marketcap)}</strong></div>
        <div><span>Liquidity</span><strong>${money(token.liquidity)}</strong></div>
        <div><span>Volume 24H</span><strong>${money(token.volume24h)}</strong></div>
        <div><span>Transactions</span><strong>${number(token.total_txns || token.txns1h)}</strong></div>
    </div>
    <div class="detail-section"><h3>🧠 SALIM AI ANALYSIS</h3>${scoreBar("AI", token.ai_score)}${scoreBar("GEM", token.gem_score)}${scoreBar("Security", token.security_score)}${scoreBar("Final", token.final_score)}</div>
    <div class="detail-section"><h3>🔐 SECURITY</h3><p>Required security threshold: <b>${securityMin}/100</b></p><p>Current security score: <b>${score(token.security_score)}/100</b></p><p>Security gate: <b>${score(token.security_score) >= securityMin ? "PASS" : "REVIEW"}</b></p></div>
    <div class="detail-section"><h3>🔗 LINKS</h3><div class="detail-links"><a href="${escapeHtml(safeUrl(token.url))}" target="_blank" rel="noopener noreferrer">Chart</a><a href="${escapeHtml(safeUrl(explorerUrl(token)))}" target="_blank" rel="noopener noreferrer">Explorer</a>${website}${x}${tg}</div></div>
    <div class="dyor">⚠️ DYOR — Not financial advice.</div>`;
    $("#detailModal").classList.remove("hidden");
    $("#detailModal").setAttribute("aria-hidden", "false");
}

function closeModal() {
    $("#detailModal").classList.add("hidden");
    $("#detailModal").setAttribute("aria-hidden", "true");
}

document.querySelectorAll("[data-close-modal]").forEach(el => el.addEventListener("click", closeModal));

$("#refreshButton").addEventListener("click", loadSignals);
$("#searchInput").addEventListener("input", event => {
    state.search = event.target.value.trim();
    render();
});

document.querySelectorAll(".filter").forEach(button => {
    button.addEventListener("click", () => {
        document.querySelectorAll(".filter").forEach(item => item.classList.remove("active"));
        button.classList.add("active");
        state.chain = button.dataset.chain;
        loadSignals();
    });
});

window.addEventListener("keydown", event => {
    if (event.key === "Escape") closeModal();
});

loadSignals();
setInterval(loadSignals, 10000);
