from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sku: str
    unit_type: str = "ea"  # 'ea' | 'lb' | 'pkg'
    price_per_unit: float = 0.0
    tax_rate: float = 0.0
    barcode: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    lots: List["Lot"] = Relationship(back_populates="product")

class Lot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id")
    lot_code: str
    packed_on: Optional[datetime] = None
    expiry: Optional[datetime] = None
    weight_lbs_total: Optional[float] = 0.0
    qty_units_total: Optional[float] = 0.0
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    product: Optional[Product] = Relationship(back_populates="lots")

class Inventory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    lot_id: int = Field(foreign_key="lot.id")
    location: str = "default"
    qty_units_available: float = 0.0
    weight_lbs_available: float = 0.0
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

class Sale(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
    items_total: float = 0.0
    tax_total: float = 0.0
    grand_total: float = 0.0
    payment_method: str = "cash"  # 'cash'|'card'|'ebt'|'other'
    customer_phone: Optional[str] = None
    notes: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

class SaleItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sale_id: int = Field(foreign_key="sale.id")
    product_id: int = Field(foreign_key="product.id")
    lot_id: Optional[int] = Field(default=None, foreign_key="lot.id")
    qty_units: float = 1.0
    weight_lbs: float = 0.0
    price_total: float = 0.0
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)
