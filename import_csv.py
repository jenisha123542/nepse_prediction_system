import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

# ── DB CONFIG ─────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "nepse_db",
    "user": "postgres",
    "password": "newpassword",
}

# ── COLUMN MAPPING ─────────────────────────────────────────────────────────────
COL_MAP = {
    "Symbol":        "symbol",
    "Conf.":         "confidence",
    "Open":          "open",
    "High":          "high",
    "Low":           "low",
    "Close":         "close",
    "LTP":           "ltp",
    "VWAP":          "vwap",
    "Vol":           "volume",
    "Prev. Close":   "prev_close",
    "Turnover":      "turnover",
    "Trans.":        "transactions",
    "Diff %":        "diff_pct",
    "Range %":       "range_pct",
    "52 Weeks High": "weeks_52_high",
    "52 Weeks Low":  "weeks_52_low",
}

# Only columns that exist in the stock_data table
DB_COLS = ["symbol", "trade_date", "confidence", "open", "high", "low", "close",
           "ltp", "vwap", "volume", "prev_close", "turnover", "transactions",
           "diff_pct", "range_pct", "weeks_52_high", "weeks_52_low"]


def clean_numeric(val):
    if pd.isna(val):
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def parse_sheet_date(sheet_name):
    """Parse sheet name like '2026_05_03' into a date object."""
    try:
        return datetime.strptime(sheet_name.strip(), "%Y_%m_%d").date()
    except ValueError:
        return None


def load_sheet(df, trade_date):
    """Clean and prepare a single sheet's dataframe."""
    # Drop S.No / Unnamed index columns
    df = df.loc[:, ~df.columns.str.match(r"^(S\.?No\.?|Unnamed)")]

    # Rename columns we care about
    df = df.rename(columns={c: COL_MAP[c] for c in df.columns if c in COL_MAP})

    # Keep only DB columns (minus trade_date which we add)
    keep = [c for c in DB_COLS if c != "trade_date" and c in df.columns]
    df = df[keep]

    # Clean numeric columns
    for col in keep:
        if col != "symbol":
            df[col] = df[col].apply(clean_numeric)

    # Drop rows with no symbol
    df = df.dropna(subset=["symbol"])
    df["symbol"] = df["symbol"].str.strip().str.upper()
    df["trade_date"] = trade_date

    return df


def import_to_db(df, conn):
    """Upsert dataframe rows into stock_data table."""
    cur = conn.cursor()

    rows = []
    for _, row in df.iterrows():
        rows.append(tuple(row.get(c) for c in DB_COLS))

    execute_values(cur, f"""
        INSERT INTO stock_data ({", ".join(DB_COLS)})
        VALUES %s
        ON CONFLICT (symbol, trade_date) DO UPDATE SET
            confidence    = EXCLUDED.confidence,
            open          = EXCLUDED.open,
            high          = EXCLUDED.high,
            low           = EXCLUDED.low,
            close         = EXCLUDED.close,
            ltp           = EXCLUDED.ltp,
            volume        = EXCLUDED.volume,
            turnover      = EXCLUDED.turnover,
            vwap          = EXCLUDED.vwap,
            prev_close    = EXCLUDED.prev_close,
            transactions  = EXCLUDED.transactions,
            diff_pct      = EXCLUDED.diff_pct,
            range_pct     = EXCLUDED.range_pct,
            weeks_52_high = EXCLUDED.weeks_52_high,
            weeks_52_low  = EXCLUDED.weeks_52_low
    """, rows)

    conn.commit()
    cur.close()
    print(f"  ✅ {len(rows)} rows imported for {df['trade_date'].iloc[0]}")


if __name__ == "__main__":
    EXCEL_PATH = r"C:\python\nepse\combined_excel.xlsx"

    print(f"Reading {EXCEL_PATH} ...")
    all_sheets = pd.read_excel(EXCEL_PATH, sheet_name=None)  # loads ALL sheets
    print(f"Found {len(all_sheets)} sheets: {list(all_sheets.keys())}")

    conn = psycopg2.connect(**DB_CONFIG)

    skipped = []
    for sheet_name, df in all_sheets.items():
        trade_date = parse_sheet_date(sheet_name)
        if trade_date is None:
            print(f"  ⚠️  Skipping '{sheet_name}' — couldn't parse date from sheet name")
            skipped.append(sheet_name)
            continue

        print(f"Processing sheet '{sheet_name}' → {trade_date} ...")
        try:
            cleaned = load_sheet(df, trade_date)
            import_to_db(cleaned, conn)
        except Exception as e:
            print(f"  ❌ Error on sheet '{sheet_name}': {e}")
            skipped.append(sheet_name)

    conn.close()

    print("\n✅ Import complete!")
    if skipped:
        print(f"⚠️  Skipped sheets: {skipped}")