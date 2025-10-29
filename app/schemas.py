from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ProductIn(BaseModel):
    name: str
    sku: str
    unit_type: str = "ea"
    price_per_unit: float = 0.0
    tax_rate: float = 0.0
    barcode: Optional[str] = None

class ProductOut(ProductIn):
    id: int
    updated_at: datetime

class LotIn(BaseModel):
    product_id: int
    lot_code: str
    packed_on: Optional[datetime] = None
    expiry: Optional[datetime] = None
    weight_lbs_total: Optional[float] = 0.0
    qty_units_total: Optional[float] = 0.0

class LotOut(LotIn):
    id: int
    updated_at: datetime

class InventoryIn(BaseModel):
    lot_id: int
    location: str = "default"
    qty_units_available: float = 0.0
    weight_lbs_available: float = 0.0

class InventoryOut(InventoryIn):
    id: int
    updated_at: datetime

class SaleItemIn(BaseModel):
    product_id: int
    lot_id: Optional[int] = None
    qty_units: float = 1.0
    weight_lbs: float = 0.0
    price_total: float = 0.0

class SaleIn(BaseModel):
    ts: Optional[datetime] = None
    items_total: float = 0.0
    tax_total: float = 0.0
    grand_total: float = 0.0
    payment_method: str = "cash"
    customer_phone: Optional[str] = None
    notes: Optional[str] = None
    items: List[SaleItemIn] = Field(default_factory=list)

class SaleOut(SaleIn):
    id: int
    updated_at: datetime
