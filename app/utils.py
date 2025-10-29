import os, httpx
from typing import Optional

def build_zpl_label(name: str, lot_code: str, weight: str, price: str, packed_on: str, qr_url: Optional[str]=None) -> str:
    # Very simple 4x6" ZPL sample; adjust for your printer
    lines = [
        '^XA',
        '^PW812',  # 203dpi -> 4" = 812 dots
        '^LH0,0',
        '^FO40,40^A0N,60,60^FD' + name[:30] + '^FS',
        '^FO40,120^A0N,40,40^FDLOT: ' + lot_code + '^FS',
        '^FO40,170^A0N,40,40^FDWeight: ' + weight + '^FS',
        '^FO40,220^A0N,40,40^FDPrice: ' + price + '^FS',
        '^FO40,270^A0N,40,40^FDPacked: ' + packed_on + '^FS',
    ]
    if qr_url:
        # 10:1 magnification, model 2
        lines.append('^FO500,40^BQN,2,10^FDLA,' + qr_url + '^FS')
    lines.append('^XZ')
    return "\n".join(lines)

async def osrm_route(osrm_url: str, coords: list[list[float]]):
    if not osrm_url:
        return None
    # coords as [[lon,lat], [lon,lat], ...]
    path = ";".join([f"{lon},{lat}" for lon, lat in coords])
    url = f"{osrm_url}/route/v1/driving/{path}?overview=full&geometries=geojson"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()

async def send_sms_via_twilio(to_number: str, body: str) -> bool:
    sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    token = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_num = os.getenv("TWILIO_FROM_NUMBER", "")
    if not (sid and token and from_num):
        return False
    # Use Twilio's REST API directly to avoid SDK
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    auth = (sid, token)
    data = {"To": to_number, "From": from_num, "Body": body}
    async with httpx.AsyncClient(timeout=10, auth=auth) as client:
        r = await client.post(url, data=data)
        return 200 <= r.status_code < 300
