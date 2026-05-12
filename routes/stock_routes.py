"""
routes/stock_routes.py  —  NepSera Market API
Table: stock_data (symbol, trade_date, open, high, low, close, ltp, vwap,
                   volume, prev_close, turnover, transactions, diff_pct,
                   range_pct, weeks_52_high, weeks_52_low, confidence)
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from database import get_db
from typing import Optional
from pydantic import BaseModel
from decimal import Decimal
import datetime

router = APIRouter(prefix="/api", tags=["market"])


# ── SCHEMAS (for admin CRUD) ───────────────────────────────────────────────────

class StockEntryCreate(BaseModel):
    symbol: str
    trade_date: datetime.date
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    close: Optional[Decimal] = None
    ltp: Optional[Decimal] = None
    vwap: Optional[Decimal] = None
    volume: Optional[Decimal] = None
    prev_close: Optional[Decimal] = None
    turnover: Optional[Decimal] = None
    transactions: Optional[int] = None
    diff_pct: Optional[Decimal] = None
    range_pct: Optional[Decimal] = None
    weeks_52_high: Optional[Decimal] = None
    weeks_52_low: Optional[Decimal] = None
    confidence: Optional[Decimal] = None

class StockEntryUpdate(BaseModel):
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    close: Optional[Decimal] = None
    ltp: Optional[Decimal] = None
    vwap: Optional[Decimal] = None
    volume: Optional[Decimal] = None
    prev_close: Optional[Decimal] = None
    turnover: Optional[Decimal] = None
    transactions: Optional[int] = None
    diff_pct: Optional[Decimal] = None
    range_pct: Optional[Decimal] = None
    weeks_52_high: Optional[Decimal] = None
    weeks_52_low: Optional[Decimal] = None
    confidence: Optional[Decimal] = None


# ── HELPER ─────────────────────────────────────────────────────────────────────

def latest_date(db: Session) -> Optional[str]:
    row = db.execute(text("SELECT MAX(trade_date) FROM stock_data")).fetchone()
    return str(row[0]) if row and row[0] else None


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN CRUD  —  /api/stocks/
#  These are the routes your admin panel calls.
# ══════════════════════════════════════════════════════════════════════════════

# ── GET /api/stocks/  — list all stocks (latest date, one row per symbol) ─────
@router.get("/stocks/")
def admin_list_stocks(
    symbol: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),   # ignored (no sector col), kept for FE compat
    status: Optional[str] = Query(None),   # ignored, same reason
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    """
    Returns one row per symbol as of the latest trade_date.
    Maps stock_data columns → what the admin frontend expects:
      ltp, change_pct (diff_pct), high_52w, low_52w, volume, symbol, company(=symbol)
    """
    trade_date = latest_date(db)
    if not trade_date:
        return []

    params: dict = {"d": trade_date, "lim": limit}
    where = "WHERE trade_date = :d"
    if symbol:
        where += " AND symbol ILIKE :sym"
        params["sym"] = f"%{symbol}%"

    rows = db.execute(text(f"""
        SELECT
            id,
            symbol,
            symbol          AS company,        -- no companies table joined yet
            trade_date,
            ltp,
            diff_pct        AS change_pct,
            weeks_52_high   AS high_52w,
            weeks_52_low    AS low_52w,
            volume,
            turnover,
            vwap,
            open,
            high,
            low,
            close,
            prev_close,
            transactions,
            confidence,
            'live'::text    AS status          -- default; update if you add a status col
        FROM stock_data
        {where}
        ORDER BY volume DESC NULLS LAST
        LIMIT :lim
    """), params).fetchall()

    return [dict(r._mapping) for r in rows]


# ── GET /api/stocks/{id}  — single row by primary key ─────────────────────────
@router.get("/stocks/{stock_id}")
def admin_get_stock(stock_id: int, db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT * FROM stock_data WHERE id = :id"),
        {"id": stock_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Stock entry not found")
    return dict(row._mapping)


# ── POST /api/stocks/  — insert a new stock_data row ─────────────────────────
@router.post("/stocks/", status_code=status.HTTP_201_CREATED)
def admin_create_stock(payload: StockEntryCreate, db: Session = Depends(get_db)):
    try:
        result = db.execute(text("""
            INSERT INTO stock_data
                (symbol, trade_date, open, high, low, close, ltp, vwap,
                 volume, prev_close, turnover, transactions,
                 diff_pct, range_pct, weeks_52_high, weeks_52_low, confidence)
            VALUES
                (:symbol, :trade_date, :open, :high, :low, :close, :ltp, :vwap,
                 :volume, :prev_close, :turnover, :transactions,
                 :diff_pct, :range_pct, :weeks_52_high, :weeks_52_low, :confidence)
            RETURNING id
        """), {
            "symbol":       payload.symbol.upper(),
            "trade_date":   payload.trade_date,
            "open":         payload.open,
            "high":         payload.high,
            "low":          payload.low,
            "close":        payload.close,
            "ltp":          payload.ltp,
            "vwap":         payload.vwap,
            "volume":       payload.volume,
            "prev_close":   payload.prev_close,
            "turnover":     payload.turnover,
            "transactions": payload.transactions,
            "diff_pct":     payload.diff_pct,
            "range_pct":    payload.range_pct,
            "weeks_52_high":payload.weeks_52_high,
            "weeks_52_low": payload.weeks_52_low,
            "confidence":   payload.confidence,
        })
        db.commit()
        new_id = result.fetchone()[0]
        return {"id": new_id, **payload.model_dump(), "symbol": payload.symbol.upper()}

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Entry for {payload.symbol.upper()} on {payload.trade_date} already exists."
        )


# ── PUT /api/stocks/{id}  — update a stock_data row ──────────────────────────
@router.put("/stocks/{stock_id}")
def admin_update_stock(stock_id: int, payload: StockEntryUpdate, db: Session = Depends(get_db)):
    # Only update fields the client actually sent (not None)
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update.")

    set_clause = ", ".join(f"{col} = :{col}" for col in updates)
    updates["stock_id"] = stock_id

    result = db.execute(
        text(f"UPDATE stock_data SET {set_clause} WHERE id = :stock_id RETURNING id"),
        updates
    )
    db.commit()

    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Stock entry not found")

    return {"id": stock_id, "updated": list(payload.model_dump(exclude_none=True).keys())}


# ── DELETE /api/stocks/{id}  — delete a stock_data row ───────────────────────
@router.delete("/stocks/{stock_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_stock(stock_id: int, db: Session = Depends(get_db)):
    result = db.execute(
        text("DELETE FROM stock_data WHERE id = :id RETURNING id"),
        {"id": stock_id}
    )
    db.commit()
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Stock entry not found")
    # 204 returns no body


# ── POST /api/stocks/sync  — placeholder for live sync trigger ────────────────
@router.post("/stocks/sync")
def admin_sync_stocks(db: Session = Depends(get_db)):
    """
    Trigger a live data sync. Wire this to your actual scraper/task.
    For now returns the latest trade_date so the frontend can confirm.
    """
    trade_date = latest_date(db)
    return {"status": "ok", "latest_trade_date": trade_date, "message": "Sync triggered"}


# ══════════════════════════════════════════════════════════════════════════════
#  EXISTING READ-ONLY ROUTES (unchanged)
# ══════════════════════════════════════════════════════════════════════════════

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


@router.get("/market/gainers")
def market_gainers(limit: int = Query(10, ge=1, le=50), on_date: Optional[str] = Query(None), db: Session = Depends(get_db)):
    trade_date = on_date or latest_date(db)
    rows = db.execute(text("""
        SELECT symbol, close, ltp, diff_pct, volume, turnover, trade_date
        FROM stock_data WHERE trade_date = :d AND diff_pct > 0
        ORDER BY diff_pct DESC LIMIT :lim
    """), {"d": trade_date, "lim": limit}).fetchall()
    return {"gainers": [dict(r._mapping) for r in rows], "trade_date": trade_date}


@router.get("/market/losers")
def market_losers(limit: int = Query(10, ge=1, le=50), on_date: Optional[str] = Query(None), db: Session = Depends(get_db)):
    trade_date = on_date or latest_date(db)
    rows = db.execute(text("""
        SELECT symbol, close, ltp, diff_pct, volume, turnover, trade_date
        FROM stock_data WHERE trade_date = :d AND diff_pct < 0
        ORDER BY diff_pct ASC LIMIT :lim
    """), {"d": trade_date, "lim": limit}).fetchall()
    return {"losers": [dict(r._mapping) for r in rows], "trade_date": trade_date}


@router.get("/market/top-volume")
def market_top_volume(limit: int = Query(10, ge=1, le=50), on_date: Optional[str] = Query(None), db: Session = Depends(get_db)):
    trade_date = on_date or latest_date(db)
    rows = db.execute(text("""
        SELECT symbol, close, ltp, volume, turnover, diff_pct, trade_date
        FROM stock_data WHERE trade_date = :d
        ORDER BY volume DESC LIMIT :lim
    """), {"d": trade_date, "lim": limit}).fetchall()
    return {"top_volume": [dict(r._mapping) for r in rows], "trade_date": trade_date}


@router.get("/market/dates")
def market_dates(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT DISTINCT trade_date FROM stock_data
        ORDER BY trade_date DESC LIMIT 90
    """)).fetchall()
    return {"dates": [str(r[0]) for r in rows]}


@router.get("/stocks/latest")
def stocks_latest(limit: int = Query(200, ge=1, le=1000), db: Session = Depends(get_db)):
    trade_date = latest_date(db)
    rows = db.execute(text("""
        SELECT symbol, close, ltp, diff_pct, volume, turnover,
               vwap, weeks_52_high, weeks_52_low, transactions, trade_date
        FROM stock_data WHERE trade_date = :d
        ORDER BY volume DESC LIMIT :lim
    """), {"d": trade_date, "lim": limit}).fetchall()
    return {"data": [dict(r._mapping) for r in rows], "trade_date": trade_date}


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
        FROM stock_data {where}
        ORDER BY trade_date ASC LIMIT :lim
    """), params).fetchall()
    return {"symbol": symbol.upper(), "data": [dict(r._mapping) for r in rows]}


@router.get("/stocks/{symbol}/summary")
def stock_summary(symbol: str, db: Session = Depends(get_db)):
    sym = symbol.upper()
    trade_date = latest_date(db)
    summary = db.execute(text("""
        SELECT MAX(weeks_52_high) AS weeks_52_high, MIN(weeks_52_low) AS weeks_52_low,
               AVG(close) AS avg_close, AVG(volume) AS avg_volume,
               SUM(turnover) AS total_turnover, COUNT(*) AS trading_days
        FROM stock_data
        WHERE symbol = :sym AND trade_date >= (CURRENT_DATE - INTERVAL '52 weeks')
    """), {"sym": sym}).fetchone()
    latest = db.execute(text("""
        SELECT trade_date, close, ltp, diff_pct, volume,
               turnover, vwap, weeks_52_high, weeks_52_low
        FROM stock_data WHERE symbol = :sym AND trade_date = :d
    """), {"sym": sym, "d": trade_date}).fetchone()
    return {
        "symbol":  sym,
        "summary": dict(summary._mapping) if summary else {},
        "latest":  dict(latest._mapping)  if latest  else {},
    }


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