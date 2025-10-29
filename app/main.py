import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from sqlmodel import select, Session
from dotenv import load_dotenv
from datetime import datetime

from db import init_db, get_session
from models import Product, Lot, Inventory, Sale, SaleItem
from schemas import ProductIn, ProductOut, LotIn, LotOut, InventoryIn, InventoryOut, SaleIn, SaleOut
from utils import build_zpl_label, osrm_route, send_sms_via_twilio

load_dotenv()

app = FastAPI(title=os.getenv("APP_NAME", "3Strands MarketOps Lite"))

# CORS: allow PWA origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static PWA
app.mount("/", StaticFiles(directory="static", html=True), name="static")

@app.on_event("startup")
def on_startup():
    init_db()

# --- Health ---
@app.get("/health", response_class=PlainTextResponse)
def health():
    return "ok"

# --- Products ---
@app.post("/api/products", response_model=ProductOut)
def create_product(body: ProductIn, session: Session = Depends(get_session)):
    prod = Product(**body.model_dump())
    session.add(prod)
    session.commit()
    session.refresh(prod)
    return prod

@app.get("/api/products", response_model=List[ProductOut])
def list_products(session: Session = Depends(get_session)):
    return session.exec(select(Product)).all()

# --- Lots ---
@app.post("/api/lots", response_model=LotOut)
def create_lot(body: LotIn, session: Session = Depends(get_session)):
    lot = Lot(**body.model_dump())
    session.add(lot)
    session.commit()
    session.refresh(lot)
    return lot

@app.get("/api/lots", response_model=List[LotOut])
def list_lots(session: Session = Depends(get_session)):
    return session.exec(select(Lot)).all()

# --- Inventory ---
@app.post("/api/inventory", response_model=InventoryOut)
def create_inventory(body: InventoryIn, session: Session = Depends(get_session)):
    inv = Inventory(**body.model_dump())
    session.add(inv)
    session.commit()
    session.refresh(inv)
    return inv

@app.get("/api/inventory", response_model=List[InventoryOut])
def list_inventory(session: Session = Depends(get_session)):
    return session.exec(select(Inventory)).all()

# --- Sales ---
@app.post("/api/sales", response_model=SaleOut)
def create_sale(body: SaleIn, session: Session = Depends(get_session)):
    sale = Sale(
        ts=body.ts or datetime.utcnow(),
        items_total=body.items_total,
        tax_total=body.tax_total,
        grand_total=body.grand_total,
        payment_method=body.payment_method,
        customer_phone=body.customer_phone,
        notes=body.notes,
    )
    session.add(sale)
    session.commit()
    for it in body.items:
        sit = SaleItem(
            sale_id=sale.id,
            product_id=it.product_id,
            lot_id=it.lot_id,
            qty_units=it.qty_units,
            weight_lbs=it.weight_lbs,
            price_total=it.price_total,
        )
        session.add(sit)
    sale.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(sale)
    return sale

@app.get("/api/sales", response_model=List[SaleOut])
def list_sales(session: Session = Depends(get_session)):
    return session.exec(select(Sale)).all()

# --- Sync (very simple timestamp-based) ---
@app.get("/api/sync/pull")
def sync_pull(since: Optional[str] = None, session: Session = Depends(get_session)):
    def parse_ts(ts):
        try:
            return datetime.fromisoformat(ts.replace("Z",""))
        except Exception:
            return datetime.min
    since_dt = parse_ts(since) if since else datetime.min

    def rows(q):
        return [r.model_dump() for r in session.exec(q).all()]

    payload = {
        "products": rows(select(Product).where(Product.updated_at > since_dt)),
        "lots": rows(select(Lot).where(Lot.updated_at > since_dt)),
        "inventory": rows(select(Inventory).where(Inventory.updated_at > since_dt)),
        "sales": rows(select(Sale).where(Sale.updated_at > since_dt)),
    }
    return JSONResponse(payload)

@app.post("/api/sync/push")
def sync_push(payload: dict, session: Session = Depends(get_session)):
    # Expect dict with keys: products, lots, inventory, sales (arrays of full objects)
    # For MVP: naive upsert by primary key presence
    def upsert(model, items):
        for data in items:
            pk = data.get("id")
            if pk:
                obj = session.get(model, pk)
                if obj:
                    for k, v in data.items():
                        if k != "id":
                            setattr(obj, k, v)
                    obj.updated_at = datetime.utcnow()
                    session.add(obj)
                else:
                    session.add(model(**data))
            else:
                session.add(model(**data))
        session.commit()

    upsert(Product, payload.get("products", []))
    upsert(Lot, payload.get("lots", []))
    upsert(Inventory, payload.get("inventory", []))
    upsert(Sale, payload.get("sales", []))

    return {"status": "ok"}

# --- Label (ZPL) ---
@app.get("/api/label/zpl", response_class=PlainTextResponse)
def label_zpl(name: str, lot: str, weight: str, price: str, packed_on: str, qr: Optional[str] = None):
    zpl = build_zpl_label(name, lot, weight, price, packed_on, qr)
    return zpl

# --- Routing via OSRM (optional) ---
@app.post("/api/route")
async def route(coords: list[list[float]]):
    osrm = os.getenv("OSRM_URL", "")
    data = await osrm_route(osrm, coords)
    if not data:
        raise HTTPException(status_code=400, detail="OSRM not configured")
    return data

# --- SMS pickup (optional Twilio) ---
@app.post("/api/sms")
async def sms(to: str, body: str):
    ok = await send_sms_via_twilio(to, body)
    return {"sent": ok}
