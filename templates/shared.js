/**
 * shared.js — NepSera
 * Drop in every page. Handles:
 *   1. Live ticker tape from API
 *   2. Auth button (sign in / account name)
 *   3. Market status badge
 *
 * Requires api.js to be loaded first.
 * Add to every page before </body>:
 *   <script src="../api.js"></script>
 *   <script src="shared.js"></script>
 */

(async function initShared() {

  // ── AUTH BUTTON ─────────────────────────────────────────────────────────────
  const btn = document.getElementById('authBtn');
  if (btn) {
    const user = localStorage.getItem('nepseraUser');
    if (user) {
      const parsed = JSON.parse(user);
      btn.textContent = '👤 ' + (parsed.name?.split(' ')[0] || 'Account');
      btn.style.cssText = 'background:rgba(16,201,138,0.1);border-color:rgba(16,201,138,0.3);color:var(--green);';
      btn.onclick = () => {
        if (confirm(`Sign out, ${parsed.name}?`)) {
          ['nepseraUser', 'nepsera_token', 'nepsera_user'].forEach(k => localStorage.removeItem(k));
          location.reload();
        }
      };
    } else {
      btn.textContent = 'Sign In';
      btn.style.cssText = 'background:rgba(61,127,255,0.1);border-color:var(--accent);color:var(--accent2);';
      btn.onclick = () => { window.location.href = 'signin.html'; };
    }
  }

  // ── MARKET STATUS BADGE ─────────────────────────────────────────────────────
  // NEPSE trades Sun–Thu 11am–3pm NST (UTC+5:45)
  function updateMarketBadge() {
    const badge = document.querySelector('.mkt-badge');
    if (!badge) return;
    const now = new Date();
    const nst = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kathmandu' }));
    const day = nst.getDay(); // 0=Sun,1=Mon,...,5=Fri,6=Sat
    const h = nst.getHours(), m = nst.getMinutes();
    const mins = h * 60 + m;
    const isWeekday = day >= 0 && day <= 4; // Sun=0 to Thu=4
    const isOpen = isWeekday && mins >= 660 && mins < 900; // 11:00–15:00

    if (isOpen) {
      badge.textContent = '● Market Open';
      badge.style.cssText = 'background:var(--green-dim);color:var(--green);border:1px solid rgba(16,201,138,0.2);font-size:11px;padding:4px 10px;border-radius:5px;font-weight:600;';
    } else {
      badge.textContent = '● Market Closed';
      badge.style.cssText = 'background:rgba(255,255,255,0.05);color:var(--text3);border:1px solid var(--border);font-size:11px;padding:4px 10px;border-radius:5px;font-weight:600;';
    }
  }
  updateMarketBadge();

  // ── LIVE TICKER ─────────────────────────────────────────────────────────────
  const tickerEl = document.getElementById('ticker');
  if (!tickerEl) return;

  // Show placeholder while loading
  tickerEl.innerHTML = `<div style="color:var(--text3);padding:0 20px;font-size:12px;font-family:'JetBrains Mono',monospace;">Loading market data...</div>`;

  try {
    const [gainersRes, losersRes] = await Promise.all([
      StockAPI.gainers(10),
      StockAPI.losers(10),
    ]);

    const gainers = gainersRes.ok ? gainersRes.data.gainers : [];
    const losers  = losersRes.ok  ? losersRes.data.losers  : [];
    const stocks  = [...gainers.slice(0, 8), ...losers.slice(0, 8)];

    if (!stocks.length) {
      tickerEl.innerHTML = `<div style="color:var(--text3);padding:0 20px;font-size:12px;">No market data available</div>`;
      return;
    }

    const makeItems = () => stocks.map(d => {
      const pct  = Number(d.diff_pct || 0);
      const sign = pct >= 0 ? '+' : '';
      const col  = pct >= 0 ? 'var(--green)' : 'var(--red)';
      return `
        <div class="ticker-item">
          <span class="sym">${d.symbol}</span>
          <span style="color:var(--text)">${fmt(d.close, 0)}</span>
          <span style="color:${col};font-size:11px;">${sign}${pct.toFixed(2)}%</span>
        </div>
        <div class="ticker-sep"></div>`;
    }).join('');

    tickerEl.innerHTML = makeItems() + makeItems();

  } catch (err) {
    console.warn('[NepSera ticker]', err);
    // Fail silently — ticker just stays as placeholder
  }

})();