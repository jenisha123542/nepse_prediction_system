from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from database import Base
import enum
from sqlalchemy import Column, Integer, String, Date, Numeric, UniqueConstraint
 
class RoleEnum(str, enum.Enum):
    user = "user"
    admin = "admin"
 
class User(Base):
    __tablename__ = "users"
 
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.user)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class StockData(Base):
    __tablename__ = "stock_data"

    id           = Column(Integer, primary_key=True, index=True)
    symbol       = Column(String(20), nullable=False, index=True)
    trade_date   = Column(Date, nullable=False, index=True)
    confidence   = Column(Numeric(10, 2))
    open         = Column(Numeric(12, 2))
    high         = Column(Numeric(12, 2))
    low          = Column(Numeric(12, 2))
    close        = Column(Numeric(12, 2))
    ltp          = Column(Numeric(12, 2))
    vwap         = Column(Numeric(12, 2))
    volume       = Column(Numeric(20, 2))
    prev_close   = Column(Numeric(12, 2))
    turnover     = Column(Numeric(20, 2))
    transactions = Column(Integer)
    diff_pct     = Column(Numeric(10, 4))
    range_pct    = Column(Numeric(10, 4))
    weeks_52_high = Column(Numeric(12, 2))
    weeks_52_low  = Column(Numeric(12, 2))

    __table_args__ = (UniqueConstraint("symbol", "trade_date", name="uq_symbol_date"),) 