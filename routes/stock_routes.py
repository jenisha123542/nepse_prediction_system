"""
routes/stock_routes.py  —  NepSera Market API
Table: stock_data (symbol, trade_date, open, high, low, close, ltp, vwap,
                   volume, prev_close, turnover, transactions, diff_pct,
                   range_pct, weeks_52_high, weeks_52_low, confidence)
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from typing import Optional

router = APIRouter(prefix="/api", tags=["market"])


# ── HELPER ─────────────────────────────────────────────────────────────────────

def latest_date(db: Session) -> Optional[str]:
    row = db.execute(text("SELECT MAX(trade_date) FROM stock_data")).fetchone()
    return str(row[0]) if row and row[0] else None


# ── /api/market/overview ───────────────────────────────────────────────────────

@router.get("/market/overview")
def market_overview(on_date: Optional[str] = Query(None), db: Session = Depends(get_db)):
    trade_date = on_date or latest_date(db)
    if not trade_date:
        return {"overview": {}}

    row = db.execute(text("""
        SELECT
            COUNT(DISTINCT symbol)                              AS total_stocks,
            SUM(volume)                                         AS total_volume,
            SUM(turnover)                                       AS total_turnover,
            SUM(transactions)                                   AS total_transactions,
            SUM(CASE WHEN diff_pct > 0  THEN 1 ELSE 0 END)     AS gainers,
            SUM(CASE WHEN diff_pct < 0  THEN 1 ELSE 0 END)     AS losers,
            SUM(CASE WHEN diff_pct = 0  THEN 1 ELSE 0 END)     AS unchanged
        FROM stock_data
        WHERE trade_date = :d
    """), {"d": trade_date}).fetchone()

    return {
        "overview": {
            "trade_date":         trade_date,
            "total_stocks":       row.total_stocks       or 0,
            "total_volume":       row.total_volume       or 0,
            "total_turnover":     row.total_turnover     or 0,
            "total_transactions": row.total_transactions or 0,
            "gainers":            row.gainers            or 0,
            "losers":             row.losers             or 0,
            "unchanged":          row.unchanged          or 0,
        }
    }


# ── /api/market/gainers ────────────────────────────────────────────────────────

@router.get("/market/gainers")
def market_gainers(
    limit: int = Query(10, ge=1, le=50),
    on_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    trade_date = on_date or latest_date(db)
    rows = db.execute(text("""
        SELECT symbol, close, ltp, diff_pct, volume, turnover, trade_date
        FROM stock_data
        WHERE trade_date = :d AND diff_pct > 0
        ORDER BY diff_pct DESC
        LIMIT :lim
    """), {"d": trade_date, "lim": limit}).fetchall()

    return {"gainers": [dict(r._mapping) for r in rows], "trade_date": trade_date}


# ── /api/market/losers ─────────────────────────────────────────────────────────

@router.get("/market/losers")
def market_losers(
    limit: int = Query(10, ge=1, le=50),
    on_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    trade_date = on_date or latest_date(db)
    rows = db.execute(text("""
        SELECT symbol, close, ltp, diff_pct, volume, turnover, trade_date
        FROM stock_data
        WHERE trade_date = :d AND diff_pct < 0
        ORDER BY diff_pct ASC
        LIMIT :lim
    """), {"d": trade_date, "lim": limit}).fetchall()

    return {"losers": [dict(r._mapping) for r in rows], "trade_date": trade_date}


# ── /api/market/top-volume ─────────────────────────────────────────────────────

@router.get("/market/top-volume")
def market_top_volume(
    limit: int = Query(10, ge=1, le=50),
    on_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    trade_date = on_date or latest_date(db)
    rows = db.execute(text("""
        SELECT symbol, close, ltp, volume, turnover, diff_pct, trade_date
        FROM stock_data
        WHERE trade_date = :d
        ORDER BY volume DESC
        LIMIT :lim
    """), {"d": trade_date, "lim": limit}).fetchall()

    return {"top_volume": [dict(r._mapping) for r in rows], "trade_date": trade_date}


# ── /api/market/dates ──────────────────────────────────────────────────────────

@router.get("/market/dates")
def market_dates(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT DISTINCT trade_date FROM stock_data
        ORDER BY trade_date DESC
        LIMIT 90
    """)).fetchall()
    return {"dates": [str(r[0]) for r in rows]}


# ── /api/stocks/latest ─────────────────────────────────────────────────────────

@router.get("/stocks/latest")
def stocks_latest(
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    trade_date = latest_date(db)
    rows = db.execute(text("""
        SELECT
            symbol, close, ltp, diff_pct, volume, turnover,
            vwap, weeks_52_high, weeks_52_low, transactions, trade_date
        FROM stock_data
        WHERE trade_date = :d
        ORDER BY volume DESC
        LIMIT :lim
    """), {"d": trade_date, "lim": limit}).fetchall()

    return {"data": [dict(r._mapping) for r in rows], "trade_date": trade_date}


# ── /api/stocks/{symbol}/history ──────────────────────────────────────────────

@router.get("/stocks/{symbol}/history")
def stock_history(
    symbol: str,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    params: dict = {"sym": symbol.upper(), "lim": limit}
    where = "WHERE symbol = :sym"
    if from_date:
        where += " AND trade_date >= :from_date"
        params["from_date"] = from_date
    if to_date:
        where += " AND trade_date <= :to_date"
        params["to_date"] = to_date

    rows = db.execute(text(f"""
        SELECT trade_date, open, high, low, close, ltp,
               volume, turnover, vwap, diff_pct, transactions
        FROM stock_data
        {where}
        ORDER BY trade_date ASC
        LIMIT :lim
    """), params).fetchall()

    return {"symbol": symbol.upper(), "data": [dict(r._mapping) for r in rows]}


# ── /api/stocks/{symbol}/summary ──────────────────────────────────────────────

@router.get("/stocks/{symbol}/summary")
def stock_summary(symbol: str, db: Session = Depends(get_db)):
    sym = symbol.upper()
    trade_date = latest_date(db)

    summary = db.execute(text("""
        SELECT
            MAX(weeks_52_high)  AS weeks_52_high,
            MIN(weeks_52_low)   AS weeks_52_low,
            AVG(close)          AS avg_close,
            AVG(volume)         AS avg_volume,
            SUM(turnover)       AS total_turnover,
            COUNT(*)            AS trading_days
        FROM stock_data
        WHERE symbol = :sym
          AND trade_date >= (CURRENT_DATE - INTERVAL '52 weeks')
    """), {"sym": sym}).fetchone()

    latest = db.execute(text("""
        SELECT trade_date, close, ltp, diff_pct, volume,
               turnover, vwap, weeks_52_high, weeks_52_low
        FROM stock_data
        WHERE symbol = :sym AND trade_date = :d
    """), {"sym": sym, "d": trade_date}).fetchone()

    return {
        "symbol":  sym,
        "summary": dict(summary._mapping) if summary else {},
        "latest":  dict(latest._mapping)  if latest  else {},
    }


# ── /api/companies ─────────────────────────────────────────────────────────────

@router.get("/companies")
def companies(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT c.symbol, c.name, s.name AS sector
        FROM companies c
        LEFT JOIN sectors s ON s.id = c.sector_id
        WHERE c.is_active = true
        ORDER BY c.symbol
    """)).fetchall()
    return {"companies": [dict(r._mapping) for r in rows]}