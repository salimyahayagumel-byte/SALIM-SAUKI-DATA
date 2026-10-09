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
        if (!dashboardCycleReady) await ensureDashboardCycle();
        const receivedSignals = Array.isArray(payload.signals) ? payload.signals : [];
        state.signals = receivedSignals.filter(token => {
            const raw = Number(token.sent_at || 0);
            const sentAtMs = raw > 0 ? (raw < 100000000000 ? raw * 1000 : raw) : 0;
            return sentAtMs >= dashboardCycleStart;
        });
        state.signals.forEach(addCalledSignal);
        render();
        renderCalledSignalsHistory();
        renderPnlTracker();
        const stamp = payload.updated_at? new Date(payload.updated_at) : new Date();
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
function number(value) { return Number(value || 0).toLocaleString(); }
function score(value) { return Math.max(0, Math.min(100, Number(value || 0))); }
function chainLabel(chain) {
    return ({ solana: "Solana", base: "Base", robinhood: "Robinhood", arc: "Arc" })[String(chain || "").toLowerCase()] || String(chain || "Unknown").toUpperCase();
}
function chainClass(chain) { return `chain-${String(chain || "unknown").toLowerCase()}`; }
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
    } catch { return "#"; }
}
function escapeHtml(value) {
    return String(value?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
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
        if (state.chain!== "all" && String(token.chain || "").toLowerCase()!== state.chain) return false;
        if (!query) return true;
        return [token.symbol, token.name, token.address, token.chain].some(value => String(value || "").toLowerCase().includes(query));
    });
}
function render() {
    const signals = filteredSignals();
    const totalVolume = signals.reduce((sum, t) => sum + Number(t.volume24h || 0), 0);
    const topScore = signals.reduce((max, t) => Math.max(max, score(t.final_score)), 0);
    const gemCount = signals.filter(t => String(t.final_status || "").toUpperCase()!== "EARLY GEM").length;
    $("#signalCount").textContent = number(signals.length);
    $("#gemCount").textContent = number(gemCount);
    $("#volume").textContent = money(totalVolume);
    $("#topScore").textContent = topScore;
    $("#feedCount").textContent = `${signals.length} signal${signals.length === 1? "" : "s"}`;
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
    const image = logo!== "#"? `<img src="${escapeHtml(logo)}" alt="${symbol}" loading="lazy" onerror="this.style.display='none'">` : `<div class="token-logo-fallback">$</div>`;
    const sentAt = token.sent_at? new Date(Number(token.sent_at) * 1000) : null;
    const age = token.pair_age_seconds? formatAge(Number(token.pair_age_seconds)) : "—";
    const buy = Number(token.buy_ratio || 0) * 100;
    const sell = Math.max(0, 100 - buy);
    const address = String(token.address || "");
    return `<article class="signal-card ${chainClass(chain)}" data-address="${escapeHtml(address)}">
        <div class="card-top"><div class="token-title"><div class="logo-wrap">${image}</div><div><div class="symbol">$${symbol}</div><div class="name">${name}</div></div></div><span class="signal-badge ${signalClass(signal)}">${signal}</span></div>
        <div class="chain-row"><span>⛓️ ${escapeHtml(chainLabel(chain))}</span><span>${sentAt? escapeHtml(sentAt.toLocaleString()) : ""}</span></div>
        <div class="market-grid"><div><span>MC</span><strong>${money(token.marketcap)}</strong></div><div><span>LIQ</span><strong>${money(token.liquidity)}</strong></div><div><span>VOL 24H</span><strong>${money(token.volume24h)}</strong></div><div><span>TXNS</span><strong>${number(token.total_txns || token.txns1h)}</strong></div></div>
        <div class="flow-row"><span>🟢 BUY ${buy.toFixed(1)}%</span><span>🔴 SELL ${sell.toFixed(1)}%</span><span>🕒 ${escapeHtml(age)}</span></div>
        <div class="scores-card">${scoreBar("🤖 AI", token.ai_score)}${scoreBar("💎 GEM", token.gem_score)}${scoreBar("🛡️ SECURITY", token.security_score)}${scoreBar("🎯 FINAL", token.final_score)}</div>
        <div class="card-links"><a href="${escapeHtml(safeUrl(token.url))}" target="_blank" rel="noopener noreferrer">📊 Chart</a><a href="${escapeHtml(safeUrl(explorerUrl(token)))}" target="_blank" rel="noopener noreferrer">🔍 Explorer</a>${token.website_url? `<a href="${escapeHtml(safeUrl(token.website_url))}" target="_blank" rel="noopener noreferrer">🌐 Web</a>` : ""}${token.twitter_url? `<a href="${escapeHtml(safeUrl(token.twitter_url))}" target="_blank" rel="noopener noreferrer">𝕏 X</a>` : ""}${token.telegram_url? `<a href="${escapeHtml(safeUrl(token.telegram_url))}" target="_blank" rel="noopener noreferrer">✈️ TG</a>` : ""}</div>
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
    const securityMin = chain === "solana"? 90 : 69;
    const website = token.website_url? `<a href="${escapeHtml(safeUrl(token.website_url))}" target="_blank" rel="noopener noreferrer">Website</a>` : "";
    const x = token.twitter_url? `<a href="${escapeHtml(safeUrl(token.twitter_url))}" target="_blank" rel="noopener noreferrer">X</a>` : "";
    const tg = token.telegram_url? `<a href="${escapeHtml(safeUrl(token.telegram_url))}" target="_blank" rel="noopener noreferrer">Telegram</a>` : "";
    $("#modalContent").innerHTML = `<div class="detail-head"><div class="eyebrow">${escapeHtml(chainLabel(chain))} · SIGNAL DETAIL</div><h2>$${escapeHtml(token.symbol || "N/A")} <span>${escapeHtml(token.name || "")}</span></h2><div class="detail-address">${escapeHtml(token.address || "")}</div></div><div class="detail-stats"><div><span>Market Cap</span><strong>${money(token.marketcap)}</strong></div><div><span>Liquidity</span><strong>${money(token.liquidity)}</strong></div><div><span>Volume 24H</span><strong>${money(token.volume24h)}</strong></div><div><span>Transactions</span><strong>${number(token.total_txns || token.txns1h)}</strong></div></div><div class="detail-section"><h3>🧠 SALIM AI ANALYSIS</h3>${scoreBar("AI", token.ai_score)}${scoreBar("GEM", token.gem_score)}${scoreBar("Security", token.security_score)}${scoreBar("Final", token.final_score)}</div><div class="detail-section"><h3>🔐 SECURITY</h3><p>Required security threshold: <b>${securityMin}/100</b></p><p>Current security score: <b>${score(token.security_score)}/100</b></p><p>Security gate: <b>${score(token.security_score) >= securityMin? "PASS" : "REVIEW"}</b></p></div><div class="detail-section"><h3>🔗 LINKS</h3><div class="detail-links"><a href="${escapeHtml(safeUrl(token.url))}" target="_blank" rel="noopener noreferrer">Chart</a><a href="${escapeHtml(safeUrl(explorerUrl(token)))}" target="_blank" rel="noopener noreferrer">Explorer</a>${website}${x}${tg}</div></div><div class="dyor">⚠️ DYOR — Not financial advice.</div>`;
    $("#detailModal").classList.remove("hidden");
    $("#detailModal").setAttribute("aria-hidden", "false");
}
function closeModal() { $("#detailModal").classList.add("hidden"); $("#detailModal").setAttribute("aria-hidden", "true"); }
document.querySelectorAll("[data-close-modal]").forEach(el => el.addEventListener("click", closeModal));
$("#refreshButton").addEventListener("click", loadSignals);
$("#searchInput").addEventListener("input", event => { state.search = event.target.value.trim(); render(); });
document.querySelectorAll(".filter").forEach(button => {
    button.addEventListener("click", () => {
        document.querySelectorAll(".filter").forEach(item => item.classList.remove("active"));
        button.classList.add("active");
        state.chain = button.dataset.chain;
        loadSignals();
    });
});
window.addEventListener("keydown", event => { if (event.key === "Escape") closeModal(); });
loadSignals();
setInterval(loadSignals, 10000);

// MASFO TOOLS
const CALLED_SIGNALS_KEY = "salim_sauki_data_calledSignals";
const DASHBOARD_CYCLE_KEY = "salim_sauki_data_dashboardCycleStartedAt";
const DASHBOARD_BOOT_KEY = "salim_sauki_data_dashboardBootId";
const DASHBOARD_CYCLE_MS = 24 * 60 * 60 * 1000;
let dashboardCycleStart = 0;
let dashboardBootId = "";
let dashboardCycleReady = false;
const PNL_REFRESH_MS = 30000;

function clearDashboardOnlyHistory() {
    try { localStorage.removeItem(CALLED_SIGNALS_KEY); } catch {}
    renderCalledSignalsHistory();
    renderPnlTracker();
}

async function ensureDashboardCycle() {
    const now = Date.now();
    let savedStart = 0;
    try { savedStart = Number(localStorage.getItem(DASHBOARD_CYCLE_KEY) || 0); } catch {}
    if (!savedStart || now - savedStart >= DASHBOARD_CYCLE_MS) {
        clearDashboardOnlyHistory();
        savedStart = now;
        try { localStorage.setItem(DASHBOARD_CYCLE_KEY, String(savedStart)); } catch {}
    }
    dashboardCycleStart = savedStart;
    try {
        const response = await fetch("/api/dashboard-cycle", { cache: "no-store", headers: { "Accept": "application/json" } });
        if (response.ok) {
            const payload = await response.json();
            const incomingBootId = String(payload.boot_id || "");
            const previousBootId = localStorage.getItem(DASHBOARD_BOOT_KEY) || "";
            if (incomingBootId && previousBootId && incomingBootId !== previousBootId) {
                clearDashboardOnlyHistory();
                dashboardCycleStart = Date.now();
                localStorage.setItem(DASHBOARD_CYCLE_KEY, String(dashboardCycleStart));
            }
            if (incomingBootId) {
                dashboardBootId = incomingBootId;
                localStorage.setItem(DASHBOARD_BOOT_KEY, incomingBootId);
            }
        }
    } catch (error) {
        console.warn("Dashboard cycle status unavailable:", error);
    }
    dashboardCycleReady = true;
}
let pnlRefreshTimer = null;
let pnlRefreshInFlight = false;
function readCalledSignals() { try { const raw = localStorage.getItem(CALLED_SIGNALS_KEY); const parsed = raw? JSON.parse(raw) : []; return Array.isArray(parsed)? parsed : []; } catch { return []; } }
function writeCalledSignals(signals) { try { localStorage.setItem(CALLED_SIGNALS_KEY, JSON.stringify(signals.slice(0, 500))); } catch {} }
function calledSignalKey(token) { const chain = String(token?.chain || token?.chainId || "unknown").toLowerCase().trim(); const address = String(token?.address || token?.baseToken?.address || "").trim().toLowerCase(); return `${chain}:${address}`; }
function addCalledSignal(token) {
    if (!token ||!token.address) return null;
    const key = calledSignalKey(token);
    if (key.endsWith(":")) return null;
    const history = readCalledSignals();
    if (history.find(item => item.key === key)) return null;
    const entry = { key, time: Number(token.sent_at || Date.now()/1000)*1000, symbol: String(token.symbol||"N/A"), name: String(token.name||"Unknown"), chain: String(token.chain||"unknown").toLowerCase(), address: String(token.address||""), entryMc: Number(token.marketcap||0), entryPrice: Number(token.price_usd||0), status: String(token.final_signal||"SIGNAL"), chartUrl: String(token.url||""), explorerUrl: String(token.explorer_url||"") };
    history.unshift(entry); writeCalledSignals(history); return entry;
}
window.addCalledSignal = addCalledSignal;
function isCalledToken(token) { return readCalledSignals().some(item => item.key === calledSignalKey(token)); }
function signalStatusClass(status) { const v=String(status||"").toUpperCase(); if(v.includes("STRONG")) return "strong"; if(v.includes("GEM")) return "gem"; if(v.includes("EARLY")) return "early"; return "other"; }
function formatHistoryTime(value) { const d=new Date(Number(value||0)); return isNaN(d.getTime())?"—":d.toLocaleString(); }
function renderCalledSignalsHistory() {
    const target=$("#calledSignalsList"); const count=$("#calledSignalsCount"); if(!target||!count) return;
    const history=readCalledSignals(); count.textContent=`${history.length} saved`;
    if(!history.length){ target.innerHTML=`<div class="empty-tool-state"><span>📭</span><p>No called signals saved in this browser yet.</p></div>`; return; }
    target.innerHTML=`<table class="history-table"><thead><tr><th>TIME</th><th>SYMBOL</th><th>CHAIN</th><th>MC AT CALL</th><th>PRICE AT CALL</th><th>ADDRESS</th><th>STATUS</th></tr></thead><tbody>${history.map(item=>`<tr><td class="muted-cell">${escapeHtml(formatHistoryTime(item.time))}</td><td class="symbol-cell">$${escapeHtml(item.symbol)}</td><td>${escapeHtml(chainLabel(item.chain))}</td><td>${money(item.entryMc)}</td><td>${formatTokenPrice(item.entryPrice)}</td><td><span class="called-link">${escapeHtml(shortAddress(item.address))}</span></td><td><span class="status-pill ${signalStatusClass(item.status)}">${escapeHtml(item.status)}</span></td></tr>`).join("")}</tbody></table>`;
}
function shortAddress(a){ const v=String(a||""); return v.length<=18?v:`${v.slice(0,8)}…${v.slice(-6)}`; }
function formatTokenPrice(v){ const n=Number(v||0); if(!isFinite(n)||n<=0) return "—"; if(n>=1) return `$${n.toLocaleString(undefined,{maximumFractionDigits:4})}`; if(n>=0.01) return `$${n.toFixed(5)}`; if(n>=0.000001) return `$${n.toFixed(8)}`; return `$${n.toExponential(4)}`; }
function pickDexPair(payload, address){ const pairs=Array.isArray(payload?.pairs)?payload.pairs:[]; const target=String(address||"").toLowerCase(); const matches=pairs.filter(p=>String(p?.baseToken?.address||"").toLowerCase()===target||String(p?.quoteToken?.address||"").toLowerCase()===target); const pool=matches.length?matches:pairs; return [...pool].sort((a,b)=>Number(b?.liquidity?.usd||0)-Number(a?.liquidity?.usd||0))[0]||null; }
function dexTokenFromPair(pair, address){
    if(!pair) return null; const target=String(address||"").toLowerCase(); const base=pair.baseToken||{}; const token=String(base.address||"").toLowerCase()===target?base:pair.quoteToken||base;
    return { name: token.name||pair.baseToken?.name||"Unknown", symbol: token.symbol||pair.baseToken?.symbol||"N/A", address: token.address||address, chainId: pair.chainId||"unknown", priceUsd: Number(pair.priceUsd||0), fdv: Number(pair.fdv||pair.marketCap||0), marketCap: Number(pair.marketCap||pair.fdv||0), liquidity: Number(pair.liquidity?.usd||0), volume24h: Number(pair.volume?.h24||0), pairUrl: pair.url||"", dexId: pair.dexId||"", pairAddress: pair.pairAddress||"", baseToken: base };
}
async function fetchDexToken(address){
    const ca=String(address||"").trim(); if(!ca) throw new Error("Please paste a contract address.");
    if(/^0x0+$/.test(ca) || ca.toLowerCase()==='0x0000000000000000000000000000000000000000'){ return null; }
    const response=await fetch(`https://api.dexscreener.com/latest/dex/tokens/${encodeURIComponent(ca)}`,{cache:"no-store",headers:{"Accept":"application/json"}});
    if(!response.ok) throw new Error(`DexScreener HTTP ${response.status}`); const payload=await response.json(); const pair=pickDexPair(payload, ca); if(!pair) return null;
    return { pair, token: dexTokenFromPair(pair, ca) };
}
function renderCaResult(result){
    const target=$("#caSearchResult"); if(!target) return;
    if(!result){ target.className="ca-result empty-tool-state"; target.innerHTML=`<span>❌</span><p>Token Not Found / Not Created on DEX</p>`; return; }
    const { token } = result; const called=isCalledToken({ chain: token.chainId, address: token.address });
    const calledBadge=called?`<span class="found-badge">✅ Already Called</span>`:`<span class="not-called-badge">🆕 Not Called Before</span>`;
    const pairLink=safeUrl(token.pairUrl); const explorer=token.chainId==="solana"?`https://solscan.io/token/${encodeURIComponent(token.address)}`:token.chainId==="base"?`https://basescan.org/token/${encodeURIComponent(token.address)}`:"#";
    target.className="ca-result"; target.innerHTML=`<div class="ca-token-card"><div class="ca-token-head"><div class="ca-token-title"><strong>$${escapeHtml(token.symbol)}</strong><span>${escapeHtml(token.name)} · ${escapeHtml(chainLabel(token.chainId))}</span></div>${calledBadge}</div><div class="tool-status success">✅ Token Found - LIVE on DEX · ${escapeHtml(token.dexId||"DEX")}</div><div class="ca-detail-grid"><div><span>CHAIN ID</span><strong>${escapeHtml(token.chainId)}</strong></div><div><span>PRICE USD</span><strong>${formatTokenPrice(token.priceUsd)}</strong></div><div><span>FDV / MC</span><strong>${money(token.fdv)}</strong></div><div><span>LIQUIDITY</span><strong>${money(token.liquidity)}</strong></div><div><span>VOLUME 24H</span><strong>${money(token.volume24h)}</strong></div><div><span>PAIR</span><strong>${escapeHtml(shortAddress(token.pairAddress))}</strong></div></div><div class="ca-links">${pairLink!=="#"?`<a href="${escapeHtml(pairLink)}" target="_blank" rel="noopener noreferrer">📊 Pair URL</a>`:""}${explorer!=="#"?`<a href="${escapeHtml(explorer)}" target="_blank" rel="noopener noreferrer">🔍 Explorer</a>`:""}</div></div>`;
}
async function searchByCa(){
    const input=$("#caSearchInput"); const button=$("#caSearchButton"); const status=$("#caSearchStatus"); const value=String(input?.value||"").trim(); if(!status||!button) return;
    if(!value){ status.className="tool-status error"; status.textContent="Please paste a contract address."; return; }
    button.disabled=true; status.className="tool-status loading"; status.textContent="Checking DexScreener…";
    try{ const result=await fetchDexToken(value); renderCaResult(result); status.className=result?"tool-status success":"tool-status error"; status.textContent=result?"Token found and currently visible on DEX.":"❌ Token Not Found / Not Created on DEX"; }catch(e){ status.className="tool-status error"; status.textContent=`❌ Lookup failed: ${e.message}`; renderCaResult(null); }finally{ button.disabled=false; }
}

// ================= FIXED PNL - NO JUMPING + HANDLE RUGS =================
function renderPnlTracker(){
    const target=$("#pnlList"); if(!target) return; const history=readCalledSignals();
    if(!history.length){ target.innerHTML=`<div class="empty-tool-state"><span>📊</span><p>Called signals will be tracked here.</p></div>`; return; }
    target.innerHTML=history.map(item=>`<div class="pnl-row"><div class="pnl-cell"><small>SYMBOL</small><strong>$${escapeHtml(item.symbol)}</strong><span class="muted-cell">${escapeHtml(chainLabel(item.chain))}</span></div><div class="pnl-cell"><small>ENTRY MC</small><strong>${money(item.entryMc)}</strong></div><div class="pnl-cell"><small>CURRENT MC</small><strong class="pnl-current-mc">—</strong></div><div class="pnl-cell"><small>CURRENT PRICE</small><strong class="pnl-current-price">—</strong></div><div class="pnl-cell"><small>PNL</small><strong class="pnl-value pnl-neutral"><span class="x-badge">—</span> <span>—</span></strong></div><a class="pnl-chart-link" href="${escapeHtml(safeUrl(item.chartUrl))}" target="_blank" rel="noopener noreferrer">Chart</a></div>`).join("");
}
async function refreshPnlTracker(){
    if(pnlRefreshInFlight) return; 
    const history=readCalledSignals(); 
    if(!history.length){ renderPnlTracker(); return; }
    pnlRefreshInFlight=true; 
    const target=$("#pnlList"); 
    if(target) target.classList.add("pnl-refreshing");
    try{
        const results=[];
        for(let i=0;i<history.length;i++){
            const item=history[i];
            try{
                if(String(item.chain||"").toLowerCase()==="robinhood"){
                    results.push({item, error:"Robinhood - Not on DexScreener", currentMc:0, currentPrice:0, pnl:null, multiple:null, chartUrl:item.chartUrl});
                } else {
                    const r=await fetchDexToken(item.address); 
                    if(!r?.token){
                        results.push({item, error:"Rugged / Pair Removed", currentMc:0, currentPrice:0, pnl:null, multiple:null, chartUrl:item.chartUrl});
                    } else {
                        const t=r.token; 
                        const cur=Number(t.marketCap||t.fdv||0); 
                        const entry=Number(item.entryMc||0); 
                        const pnl=entry>0&&cur>0?((cur-entry)/entry)*100:null; 
                        const mult=entry>0&&cur>0?cur/entry:null; 
                        results.push({item, currentMc:cur, currentPrice:Number(t.priceUsd||0), pnl, multiple:mult, chartUrl:t.pairUrl||item.chartUrl});
                    }
                }
            }catch(e){ 
                results.push({item, error:e.message||"Fetch failed", currentMc:0, currentPrice:0, pnl:null, multiple:null, chartUrl:item.chartUrl});
            }
            if(i<history.length-1) await new Promise(r=>setTimeout(r, 350));
        }
        if(!target) return; 
        target.innerHTML=results.map(result=>{ 
            const item=result.item; 
            const pnl=result.pnl; 
            const mult=result.multiple; 
            const cls=Number.isFinite(pnl)?(pnl>0?"pnl-positive":pnl<0?"pnl-negative":"pnl-neutral"):"pnl-neutral"; 
            const pnlText=Number.isFinite(pnl)?`${pnl>=0?"+":""}${pnl.toFixed(2)}%`:"—"; 
            const multText=Number.isFinite(mult)&&mult>0?`${mult.toFixed(2)}x`:"—"; 
            const cur=Number.isFinite(result.currentMc)&&result.currentMc>0?money(result.currentMc):"—"; 
            const price=Number.isFinite(result.currentPrice)&&result.currentPrice>0?formatTokenPrice(result.currentPrice):"—"; 
            const chart=safeUrl(result.chartUrl||item.chartUrl);
            const hasErr=!!result.error && !Number.isFinite(pnl);
            return `<div class="pnl-row"><div class="pnl-cell"><small>SYMBOL</small><strong>$${escapeHtml(item.symbol)}</strong><span class="muted-cell">${escapeHtml(chainLabel(item.chain))}</span></div><div class="pnl-cell"><small>ENTRY MC</small><strong>${money(item.entryMc)}</strong></div><div class="pnl-cell"><small>CURRENT MC</small><strong>${cur}</strong></div><div class="pnl-cell"><small>CURRENT PRICE</small><strong>${price}</strong></div><div class="pnl-cell"><small>PNL / MULTIPLE</small><strong class="${cls}"><span class="x-badge">${multText}</span> ${pnlText}</strong>${hasErr?`<span class="pnl-error">${escapeHtml(result.error)}</span>`:""}</div><a class="pnl-chart-link" href="${escapeHtml(chart)}" target="_blank" rel="noopener noreferrer">Chart</a></div>`; 
        }).join("");
        const stamp=$("#pnlUpdatedAt"); if(stamp) stamp.textContent=`Updated ${new Date().toLocaleTimeString()}`;
    }finally{ pnlRefreshInFlight=false; if(target) target.classList.remove("pnl-refreshing"); }
}
function initDashboardTools(){
    renderCalledSignalsHistory(); renderPnlTracker();
    $("#caSearchButton")?.addEventListener("click", searchByCa);
    $("#caSearchInput")?.addEventListener("keydown", e=>{ if(e.key==="Enter") searchByCa(); });
    $("#clearCalledSignals")?.addEventListener("click", ()=>{ if(!readCalledSignals().length) return; if(!confirm("Clear all locally saved called signals?")) return; localStorage.removeItem(CALLED_SIGNALS_KEY); renderCalledSignalsHistory(); renderPnlTracker(); });
    refreshPnlTracker(); if(pnlRefreshTimer) clearInterval(pnlRefreshTimer); pnlRefreshTimer=setInterval(refreshPnlTracker, PNL_REFRESH_MS);
}
initDashboardTools();

// TOP TABS LOGIC
function initTopTabs(){
    const tabs=document.querySelectorAll('.tab-button');
    const views=document.querySelectorAll('.view-panel');
    const filters=document.getElementById('signalsFilters');
    tabs.forEach(btn=>{
        btn.addEventListener('click',()=>{
            const view=btn.dataset.view;
            tabs.forEach(b=>b.classList.remove('active'));
            btn.classList.add('active');
            views.forEach(v=>v.classList.remove('active'));
            document.getElementById(`view-${view}`)?.classList.add('active');
            if(filters) filters.style.display = view==='signals'? 'flex' : 'none';
            localStorage.setItem('salim_active_view', view);
        });
    });
    const saved=localStorage.getItem('salim_active_view')||'signals';
    const target=document.querySelector(`.tab-button[data-view="${saved}"]`);
    if(target) target.click(); else tabs[0]?.classList.add('active');
}
initTopTabs();
