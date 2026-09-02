async function scanTokens() {

    const button = document.querySelector(".scan-button");

    button.disabled = true;

    button.textContent = "🔎 SCANNING...";

    try {

        const response = await fetch("/api/scan");

        if (!response.ok) {
            throw new Error("Scan failed");
        }

        const data = await response.json();

        renderTokens(data);

    } catch (error) {

        console.error(error);

        alert("❌ Scanner error. Check the server.");

    } finally {

        button.disabled = false;

        button.textContent = "🔎 SCAN SOLANA";
    }
}


function money(value) {

    value = Number(value || 0);

    if (value >= 1000000) {
        return "$" + (value / 1000000).toFixed(2) + "M";
    }

    if (value >= 1000) {
        return "$" + (value / 1000).toFixed(1) + "K";
    }

    return "$" + value.toFixed(0);
}


function renderTokens(tokens) {

    const grid = document.getElementById("tokenGrid");

    if (!Array.isArray(tokens) || tokens.length === 0) {

        grid.innerHTML = `
            <div class="empty-state">
                <div>💎</div>
                <h3>No signals found</h3>
                <p>
                    No qualifying Solana GEM was detected.
                </p>
            </div>
        `;

        return;
    }


    const recommended = tokens.filter(
        token => token.is_recommended
    );


    document.getElementById("gemCount").textContent =
        recommended.length;


    const totalVolume = tokens.reduce(
        (sum, token) =>
            sum + Number(token.volume24h || 0),
        0
    );


    document.getElementById("volume").textContent =
        money(totalVolume);


    const topScore = Math.max(
        ...tokens.map(
            token =>
                Number(token.final_score || 0)
        )
    );


    document.getElementById("topScore").textContent =
        topScore;


    const securityPassed = tokens.filter(
        token =>
            Number(token.security_score || 0) >= 90
    ).length;


    document.getElementById("securityCount").textContent =
        securityPassed;


    grid.innerHTML = tokens
        .slice(0, 12)
        .map(tokenCard)
        .join("");
}


function tokenCard(token) {

    const symbol =
        escapeHtml(token.symbol || "N/A");

    const name =
        escapeHtml(token.name || "Unknown");

    const signal =
        escapeHtml(
            token.final_signal ||
            token.gem_signal ||
            "NO SIGNAL"
        );


    const logo =
        token.image_url ||
        "https://via.placeholder.com/80";


    const ai =
        Number(token.ai_score || 0);

    const gem =
        Number(token.gem_score || 0);

    const security =
        Number(token.security_score || 0);

    const final =
        Number(token.final_score || 0);


    const address =
        encodeURIComponent(
            token.address || ""
        );


    return `

        <article class="token-card">

            <div class="token-header">

                <div class="token-name">

                    <img
                        class="token-logo"
                        src="${escapeAttribute(logo)}"
                        alt="${symbol}"
                    >

                    <div>

                        <div class="token-symbol">
                            $${symbol}
                        </div>

                        <div class="token-full-name">
                            ${name}
                        </div>

                    </div>

                </div>

                <div class="signal">
                    ${signal}
                </div>

            </div>


            <div class="token-data">

                <div class="data-box">
                    <span>MARKET CAP</span>
                    <strong>
                        ${money(token.marketcap)}
                    </strong>
                </div>

                <div class="data-box">
                    <span>LIQUIDITY</span>
                    <strong>
                        ${money(token.liquidity)}
                    </strong>
                </div>

                <div class="data-box">
                    <span>VOLUME 24H</span>
                    <strong>
                        ${money(token.volume24h)}
                    </strong>
                </div>

                <div class="data-box">
                    <span>BUY RATIO</span>
                    <strong>
                        ${(Number(token.buy_ratio || 0) * 100).toFixed(1)}%
                    </strong>
                </div>

            </div>


            <div class="scores">

                ${scoreBar("🤖 AI", ai)}

                ${scoreBar("💎 GEM", gem)}

                ${scoreBar("🔐 SECURITY", security)}

                ${scoreBar("🎯 FINAL", final)}

            </div>


            <div class="token-links">

                <a
                    href="${token.url || '#'}"
                    target="_blank"
                >
                    📊 DEX
                </a>

                <a
                    href="https://solscan.io/token/${address}"
                    target="_blank"
                >
                    🔍 SOLSCAN
                </a>

                <a
                    href="https://gmgn.ai/sol/token/${address}"
                    target="_blank"
                >
                    👁 GMGN
                </a>

            </div>

        </article>
    `;
}


function scoreBar(label, score) {

    score = Math.max(
        0,
        Math.min(
            100,
            Number(score || 0)
        )
    );


    return `

        <div class="score-row">

            <span>${label}</span>

            <strong>
                ${score}/100
            </strong>

        </div>

        <div class="score-bar">

            <div
                class="score-fill"
                style="width:${score}%"
            ></div>

        </div>

    `;
}


function escapeHtml(value) {

    return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function escapeAttribute(value) {

    return escapeHtml(value);
}
