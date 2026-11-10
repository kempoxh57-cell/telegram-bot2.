import subprocess
import json
import io
import time
import urllib.parse
import requests
import qrcode
from PIL import Image, ImageDraw
import config

DEFAULT_GATEWAY_URL = getattr(config, "BAKONG_GATEWAY_URL", "https://lorndavid.online").rstrip("/")
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json"
}

def check_gateway_health(gateway_url: str = None) -> dict:
    """
    Checks the connectivity and status of the Bakong KHQR gateway.
    """
    url = (gateway_url or DEFAULT_GATEWAY_URL).rstrip("/")
    try:
        r = requests.get(f"{url}/api/v1/admin/accounts/list", headers=DEFAULT_HEADERS, timeout=6)
        if r.status_code == 200:
            return {"online": True, "status": "operational", "url": url}
        return {"online": False, "status": f"HTTP {r.status_code}", "url": url}
    except Exception as e:
        return {"online": False, "error": str(e), "url": url}

def check_bakong_transaction(md5_hash: str, token: str = "", gateway_url: str = None) -> dict:
    """
    Checks the NBC Bakong payment settlement status by MD5 hash using:
    1. Primary: LuyRiel Bakong KHQR Gateway API (https://www.lorndavid.online/docs)
       Endpoint: GET /api/v1/check/{md5}
       responseCode == 0 -> Confirmed on NBC ledger.
       responseCode == 1 -> Pending / unconfirmed.
    2. Fallback: Official NBC Bakong Open API (if BAKONG_API_TOKEN is provided)
    """
    if not md5_hash or not md5_hash.strip():
        return {"paid": False, "error": "MD5_HASH_REQUIRED"}

    clean_md5 = md5_hash.strip().lower()
    base_gw = (gateway_url or DEFAULT_GATEWAY_URL).rstrip("/")

    # 1. Primary: LuyRiel Gateway (/api/v1/check/:md5)
    try:
        url = f"{base_gw}/api/v1/check/{clean_md5}"
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=7)
        if r.status_code == 200:
            res = r.json()
            if res.get("responseCode") == 0:
                return {
                    "paid": True,
                    "data": res.get("data") or {},
                    "source": "lorndavid_gateway",
                    "hash": res.get("hash", clean_md5)
                }
            if res.get("responseCode") == 1:
                return {
                    "paid": False,
                    "message": res.get("responseMessage", "Pending on NBC network"),
                    "source": "lorndavid_gateway"
                }
    except Exception:
        # Gateway request failed, proceed to fallback
        pass

    # 2. Alternative POST body check on gateway
    try:
        post_url = f"{base_gw}/api/v1/check"
        r = requests.post(post_url, json={"md5": clean_md5}, headers=DEFAULT_HEADERS, timeout=7)
        if r.status_code == 200:
            res = r.json()
            if res.get("responseCode") == 0:
                return {
                    "paid": True,
                    "data": res.get("data") or {},
                    "source": "lorndavid_gateway_post",
                    "hash": res.get("hash", clean_md5)
                }
            if res.get("responseCode") == 1:
                return {
                    "paid": False,
                    "message": res.get("responseMessage", "Pending on NBC network"),
                    "source": "lorndavid_gateway_post"
                }
    except Exception:
        pass

    # 3. Fallback: Official NBC Bakong API (if admin configured token)
    if token and token.strip():
        try:
            nbc_url = "https://api-bakong.nbc.gov.kh/v1/check_transaction_by_md5"
            nbc_headers = {
                "Authorization": f"Bearer {token.strip()}",
                "Content-Type": "application/json"
            }
            r = requests.post(nbc_url, json={"md5": clean_md5}, headers=nbc_headers, timeout=5)
            res = r.json()
            if res.get("responseCode") == 0 and res.get("data"):
                return {"paid": True, "data": res.get("data"), "source": "official_nbc"}
            if res.get("status", {}).get("code") == 0 and res.get("data"):
                return {"paid": True, "data": res.get("data"), "source": "official_nbc"}
            return {"paid": False, "message": res.get("responseMessage", "Pending"), "source": "official_nbc"}
        except Exception as e:
            return {"paid": False, "error": str(e)}

    return {"paid": False, "message": "Transaction pending or gateway unconfirmed"}

def generate_deeplink(qr_string: str) -> str:
    """
    Constructs a mobile 1-tap Bakong app deep link according to NBC Bakong specification.
    """
    enc_qr = urllib.parse.quote(qr_string)
    return f"https://bakong.page.link/?link={enc_qr}&apn=kh.gov.nbc.bakong&ibi=kh.gov.nbc.bakong&isi=1450098909"

def generate_khqr_data(account_id: str, merchant_name: str, amount: float, currency: str = "USD", bill_number: str = "", gateway_url: str = None) -> dict:
    """
    Generates dynamic KHQR payment string, MD5 settlement hash, and 1-tap deep link.
    Supports both LuyRiel Gateway API and local BakongKHQR engine as fallback.
    """
    bill_no = bill_number or f"DEP{int(time.time()) % 100000}"
    base_gw = (gateway_url or DEFAULT_GATEWAY_URL).rstrip("/")

    # Attempt 1: LuyRiel Gateway API (POST /api/v1/khqr/generate)
    try:
        gw_payload = {
            "accountId": account_id,
            "merchantName": merchant_name,
            "merchantCity": getattr(config, "BAKONG_MERCHANT_CITY", "PHNOM PENH"),
            "amount": float(amount),
            "currency": currency.upper(),
            "billNumber": bill_no,
            "storeLabel": "Telegram Bot"
        }
        r = requests.post(f"{base_gw}/api/v1/khqr/generate", json=gw_payload, headers=DEFAULT_HEADERS, timeout=6)
        if r.status_code == 200:
            data = r.json()
            qr_str = data.get("qrString") or data.get("qr")
            md5_str = data.get("md5")
            if qr_str and md5_str:
                deeplink = data.get("deeplink") or generate_deeplink(qr_str)
                return {
                    "qr": qr_str,
                    "md5": md5_str,
                    "deeplink": deeplink,
                    "billNumber": bill_no,
                    "source": "gateway"
                }
    except Exception:
        # Fall back to local Node.js bakong-khqr SDK
        pass

    # Attempt 2: Local bakong-khqr Node.js engine
    curr = "usd" if currency.upper() == "USD" else "khr"
    js_code = f"""
    const {{ BakongKHQR, khqrData, IndividualInfo }} = require('bakong-khqr');
    const khqr = new BakongKHQR();
    const curr = '{curr}' === 'khr' ? khqrData.currency.khr : khqrData.currency.usd;
    const info = new IndividualInfo(
      '{account_id}',
      '{merchant_name}',
      'PHNOM PENH',
      {{
        currency: curr,
        amount: {float(amount)},
        billNumber: '{bill_no}',
        expirationTimestamp: Date.now() + 60 * 60 * 1000
      }}
    );
    const res = khqr.generateIndividual(info);
    console.log(JSON.stringify(res));
    """
    try:
        out = subprocess.check_output(["node", "-e", js_code], text=True, stderr=subprocess.STDOUT)
        res = json.loads(out)
        if res.get("status", {}).get("code") == 0 and res.get("data"):
            qr_str = res["data"]["qr"]
            md5_str = res["data"]["md5"]
            deeplink = generate_deeplink(qr_str)
            return {
                "qr": qr_str,
                "md5": md5_str,
                "deeplink": deeplink,
                "billNumber": bill_no,
                "source": "local_sdk"
            }
        else:
            err = res.get("status", {}).get("message", "Unknown KHQR error")
            raise RuntimeError(f"KHQR generation failed: {err}")
    except Exception as e:
        raise RuntimeError(f"Failed to generate KHQR: {e}")

def create_khqr_card(qr_string: str, amount_str: str, merchant_name: str, account_id: str) -> io.BytesIO:
    """
    Renders a branded KHQR card with red banner, QR code, merchant name, and amount.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(qr_string)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    card_width = max(qr_img.width + 60, 380)
    card_height = qr_img.height + 150

    card = Image.new("RGB", (card_width, card_height), "#FFFFFF")
    draw = ImageDraw.Draw(card)

    # KHQR Header (Bakong Red)
    red_color = (226, 27, 34)
    draw.rectangle([(0, 0), (card_width, 55)], fill=red_color)
    draw.text((card_width // 2, 27), "KHQR", fill="white", anchor="mm")

    # Center QR
    qr_x = (card_width - qr_img.width) // 2
    qr_y = 70
    card.paste(qr_img, (qr_x, qr_y))

    # Details at bottom
    text_y = qr_y + qr_img.height + 18
    draw.text((card_width // 2, text_y), f"Merchant: {merchant_name}", fill="#111111", anchor="mm")
    draw.text((card_width // 2, text_y + 22), f"Account: {account_id}", fill="#666666", anchor="mm")
    draw.text((card_width // 2, text_y + 44), f"Amount: {amount_str}", fill=red_color, anchor="mm")

    # Border
    draw.rectangle([(0, 0), (card_width - 1, card_height - 1)], outline="#DDDDDD", width=2)

    buf = io.BytesIO()
    card.save(buf, format="PNG")
    buf.seek(0)
    return buf
