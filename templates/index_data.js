/**
 * index_data.js  —  NepSera Dashboard Live Data
 * Drop this file next to index.html and add:
 *   <script src="../api.js"></script>
 *   <script src="index_data.js"></script>
 * just before </body> in index.html
 */

(async function loadDashboard() {

  // ── TICKER + OVERVIEW + MOVERS all use the same latest data ────────────────
  const [overviewRes, gainersRes, losersRes, topVolRes] = await Promise.all([
    StockAPI.overview(),
    StockAPI.gainers(10),
    StockAPI.losers(10),
    StockAPI.topVolume(10),
  ]);

  const overview = overviewRes.ok ? overviewRes.data.overview : null;
  const gainers  = gainersRes.ok  ? gainersRes.data.gainers   : [];
  const losers   = losersRes.ok   ? losersRes.data.losers     : [];
  const topVol   = topVolRes.ok   ? topVolRes.data.top_volume : [];

  // ── HERO STRIP ─────────────────────────────────────────────────────────────
  if (overview) {
    // Turnover
    const heroTurnover = document.querySelector('.hero-stats .hero-stat:nth-child(1) .hstat-v');
    if (heroTurnover) heroTurnover.textContent = fmtTurnover(overview.total_turnover);

    // Shares traded
    const heroVol = document.querySelector('.hero-stats .hero-stat:nth-child(2) .hstat-v');
    if (heroVol) heroVol.textContent = fmtVol(overview.total_volume);

    // Transactions
    const heroTx = document.querySelector('.hero-stats .hero-stat:nth-child(3) .hstat-v');
    if (heroTx) heroTx.textContent = Number(overview.total_transactions || 0).toLocaleString();

    // Data date in page subtitle if it exists
    const dateEl = document.getElementById('dataDate');
    if (dateEl) dateEl.textContent = 'Data as of: ' + (overview.trade_date || '');
  }

  // ── TICKER TAPE ────────────────────────────────────────────────────────────
  // Combine gainers + losers for a balanced ticker
  const tickerStocks = [...gainers.slice(0, 8), ...losers.slice(0, 8)];
  if (tickerStocks.length) {
    const ticker = document.getElementById('ticker');
    if (ticker) {
      const makeItems = () => tickerStocks.map(d => {
        const pct = Number(d.diff_pct || 0);
        const sign = pct >= 0 ? '+' : '';
        const col = pct >= 0 ? 'var(--green)' : 'var(--red)';
        return `
          <div class="ticker-item">
            <span class="sym">${d.symbol}</span>
            <span class="val">${fmt(d.close, 0)}</span>
            <span class="chg" style="color:${col}">${sign}${pct.toFixed(2)}%</span>
          </div>
          <div class="ticker-sep"></div>`;
      }).join('');
      ticker.innerHTML = makeItems() + makeItems();
    }
  }

  // ── QUICK MOVERS TABLE (Overview tab) ──────────────────────────────────────
  const quickMoversBody = document.querySelector('#pane-overview .tbl tbody');
  if (quickMoversBody && (gainers.length || losers.length)) {
    // Show top 2 gainers + top 2 losers
    const movers = [
      ...gainers.slice(0, 2),
      ...losers.slice(0, 2),
    ];
    quickMoversBody.innerHTML = movers.map(r => {
      const pct = Number(r.diff_pct || 0);
      const isUp = pct >= 0;
      return `
        <tr>
          <td style="font-weight:700;font-family:'JetBrains Mono',monospace;">${r.symbol}</td>
          <td>NPR ${fmt(r.close, 0)}</td>
          <td><span class="bdg ${isUp ? 'bdg-u' : 'bdg-d'}">${isUp ? '+' : ''}${pct.toFixed(2)}%</span></td>
        </tr>`;
    }).join('');
  }

  // ── GAINERS TABLE (Movers tab) ─────────────────────────────────────────────
  const gainersBody = document.querySelector('#pane-movers .g2e .card:first-child .tbl tbody');
  if (gainersBody && gainers.length) {
    gainersBody.innerHTML = gainers.slice(0, 5).map(r => `
      <tr>
        <td style="font-weight:700;font-family:'JetBrains Mono',monospace;">${r.symbol}</td>
        <td style="font-family:'JetBrains Mono',monospace;">${fmt(r.ltp || r.close, 0)}</td>
        <td><span class="bdg bdg-u">+${Number(r.diff_pct).toFixed(2)}%</span></td>
        <td style="color:var(--text3);font-family:'JetBrains Mono',monospace;font-size:12px;">${fmtVol(r.volume)}</td>
      </tr>`).join('');
  }

  // ── LOSERS TABLE (Movers tab) ──────────────────────────────────────────────
  const losersBody = document.querySelector('#pane-movers .g2e .card:last-child .tbl tbody');
  if (losersBody && losers.length) {
    losersBody.innerHTML = losers.slice(0, 5).map(r => `
      <tr>
        <td style="font-weight:700;font-family:'JetBrains Mono',monospace;">${r.symbol}</td>
        <td style="font-family:'JetBrains Mono',monospace;">${fmt(r.ltp || r.close, 0)}</td>
        <td><span class="bdg bdg-d">${Number(r.diff_pct).toFixed(2)}%</span></td>
        <td style="color:var(--text3);font-family:'JetBrains Mono',monospace;font-size:12px;">${fmtVol(r.volume)}</td>
      </tr>`).join('');
  }

  // ── MOVERS CHART (Volume bar chart) ───────────────────────────────────────
  // Replace the static buildMoverChart() with real data
  const moverCanvas = document.getElementById('moverChart');
  if (moverCanvas && (gainers.length || losers.length)) {
    const top5g = gainers.slice(0, 5);
    const top5l = losers.slice(0, 5);
    const labels = [...top5g.map(r => r.symbol), ...top5l.map(r => r.symbol)];
    const volumes = [
      ...top5g.map(r => Math.round(Number(r.volume || 0) / 1000)),
      ...top5l.map(r => -Math.round(Number(r.volume || 0) / 1000)),
    ];

    // Destroy the old static chart if it exists
    const existing = Chart.getChart(moverCanvas);
    if (existing) existing.destroy();

    new Chart(moverCanvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data: volumes,
          backgroundColor: ctx => ctx.raw >= 0
            ? 'rgba(16,201,138,0.75)'
            : 'rgba(240,82,82,0.75)',
          borderRadius: 4,
          borderSkipped: false,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false, drawBorder: false } },
          y: {
            grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
            ticks: { callback: v => Math.abs(v) + 'K' },
          },
        },
      },
    });
    window._moverBuilt = true; // prevent static version from overwriting
  }

  // ── AI MARKET SIGNAL (dynamic gainers/losers count) ────────────────────────
  if (overview) {
    const g = overview.gainers || 0;
    const l = overview.losers  || 0;
    const total = g + l || 1;
    const bullPct = Math.round((g / total) * 100);

    let signal, signalColor, signalDesc;
    if (bullPct >= 65) {
      signal = 'Strongly Bullish';
      signalColor = 'var(--green)';
      signalDesc = `${g} stocks advancing vs ${l} declining (${bullPct}% breadth). Strong broad-based rally across NEPSE sectors.`;
    } else if (bullPct >= 55) {
      signal = 'Moderately Bullish';
      signalColor = 'var(--green)';
      signalDesc = `${g} gainers vs ${l} losers today. Positive market breadth with selective sector strength.`;
    } else if (bullPct >= 45) {
      signal = 'Mixed Signals';
      signalColor = 'var(--gold)';
      signalDesc = `Market is split — ${g} gainers, ${l} losers. Sector rotation in play. Exercise selective caution.`;
    } else {
      signal = 'Cautiously Bearish';
      signalColor = 'var(--red)';
      signalDesc = `${l} stocks declining vs ${g} advancing (${100 - bullPct}% negative breadth). Broad selling pressure observed.`;
    }

    // Update AI Signal card in Overview tab
    const signalEl = document.querySelector('#pane-overview .card:last-child div[style*="DM Serif"]');
    if (signalEl) {
      signalEl.textContent = signal;
      signalEl.style.color = signalColor;
    }
    const descEl = document.querySelector('#pane-overview .card:last-child div[style*="line-height:1.75"]');
    if (descEl) descEl.textContent = signalDesc;

    // Update Market Mood in News tab too
    const moodVal = document.querySelector('.mood-val');
    if (moodVal) { moodVal.textContent = signal; moodVal.style.color = signalColor; }
    const moodDesc = document.querySelector('.mood-desc');
    if (moodDesc) moodDesc.textContent = signalDesc;
  }

})().catch(err => console.error('[NepSera dashboard]', err));