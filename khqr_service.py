import hashlib
import io
import json
import time
import urllib.parse
import requests

try:
    import qrcode
    from PIL import Image, ImageDraw
    QRCODE_AVAILABLE = True
except ImportError:
    qrcode = None
    Image = None
    ImageDraw = None
    QRCODE_AVAILABLE = False

import config

DEFAULT_GATEWAY_URL = getattr(config, "BAKONG_GATEWAY_URL", "https://lorndavid.online").rstrip("/")
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json"
}

# CRC-16/CCITT-FALSE Lookup Table (Polynomial 0x1021, Init 0xFFFF)
CRC_TABLE = [
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7,
    0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6,
    0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485,
    0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4,
    0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC,
    0x48C4, 0x58E5, 0x6886, 0x78A7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xC9CC, 0xD9ED, 0xE98E, 0xF9AF, 0x8948, 0x9969, 0xA90A, 0xB92B,
    0x5AF5, 0x4AD4, 0x7AB7, 0x6A96, 0x1A71, 0x0A50, 0x3A33, 0x2A12,
    0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E, 0x9B79, 0x8B58, 0xBB3B, 0xAB1A,
    0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41,
    0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49,
    0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70,
    0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78,
    0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F,
    0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E,
    0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D,
    0x34E2, 0x24C3, 0x14A0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xA7DB, 0xB7FA, 0x8799, 0x97B8, 0xE75F, 0xF77E, 0xC71D, 0xD73C,
    0x26D3, 0x36F2, 0x0691, 0x16B0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xD94C, 0xC96D, 0xF90E, 0xE92F, 0x99C8, 0x89E9, 0xB98A, 0xA9AB,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18C0, 0x08E1, 0x3882, 0x28A3,
    0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E, 0x8BF9, 0x9BD8, 0xABBB, 0xBB9A,
    0x4A75, 0x5A54, 0x6A37, 0x7A16, 0x0AF1, 0x1AD0, 0x2AB3, 0x3A92,
    0xFD2E, 0xED0F, 0xDD6C, 0xCD4D, 0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9,
    0x7C26, 0x6C07, 0x5C64, 0x4C45, 0x3CA2, 0x2C83, 0x1CE0, 0x0CC1,
    0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C, 0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8,
    0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0,
]

def calculate_crc16(data: str) -> str:
    """
    Computes CRC-16/CCITT-FALSE checksum for EMVCo QR code standard (Tag 63).
    """
    crc = 0xFFFF
    for b in data.encode("utf-8"):
        j = (b ^ (crc >> 8)) & 0xFF
        crc = CRC_TABLE[j] ^ ((crc << 8) & 0xFFFF)
    return f"{crc:04X}"

def _emv_format(tag: str, value: str) -> str:
    """
    Encodes tag and value into EMVCo format: TTLL<value>
    """
    s = str(value)
    return f"{tag}{len(s):02d}{s}"

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
    Uses pure Python EMVCo KHQR generation (zero external Node.js dependencies).
    """
    bill_no = bill_number or f"DEP{int(time.time()) % 100000}"
    clean_account = (account_id or "").strip()
    clean_name = (merchant_name or "Bakong Merchant").strip()[:25]
    clean_city = getattr(config, "BAKONG_MERCHANT_CITY", "PHNOM PENH")[:15]
    curr_upper = currency.upper()

    try:
        now_ms = int(time.time() * 1000)
        exp_ms = now_ms + (3600 * 1000)  # 1 hour expiration

        # 00: Payload Format Indicator (01)
        out = _emv_format("00", "01")
        # 01: Point of Initiation Method (12 = Dynamic QR)
        out += _emv_format("01", "12")
        # 29: Merchant Account Information Individual
        acc_sub = _emv_format("00", clean_account)
        out += _emv_format("29", acc_sub)
        # 52: Merchant Category Code (Default: 5999)
        out += _emv_format("52", "5999")
        # 53: Transaction Currency (840 = USD, 116 = KHR)
        curr_code = "840" if curr_upper == "USD" else "116"
        out += _emv_format("53", curr_code)
        # 54: Transaction Amount
        if curr_upper == "KHR":
            amt_str = str(int(round(float(amount))))
        else:
            amt_float = float(amount)
            amt_str = str(int(amt_float)) if amt_float == int(amt_float) else f"{amt_float:.2f}"
        out += _emv_format("54", amt_str)
        # 58: Country Code (KH)
        out += _emv_format("58", "KH")
        # 59: Merchant Name
        out += _emv_format("59", clean_name)
        # 60: Merchant City
        out += _emv_format("60", clean_city)
        # 62: Additional Data (Bill Number)
        if bill_no:
            add_sub = _emv_format("01", bill_no[:25])
            out += _emv_format("62", add_sub)
        # 99: Timestamp (Creation + Expiration)
        ts_sub = _emv_format("00", str(now_ms)) + _emv_format("01", str(exp_ms))
        out += _emv_format("99", ts_sub)

        # 63: CRC16-CCITT Checksum
        check_str = out + "6304"
        crc = calculate_crc16(check_str)
        qr_string = check_str + crc

        md5_hash = hashlib.md5(qr_string.encode("utf-8")).hexdigest()
        deeplink = generate_deeplink(qr_string)

        return {
            "qr": qr_string,
            "md5": md5_hash,
            "deeplink": deeplink,
            "billNumber": bill_no,
            "source": "native_python"
        }
    except Exception as e:
        # Fallback to Gateway API if native generation fails
        base_gw = (gateway_url or DEFAULT_GATEWAY_URL).rstrip("/")
        try:
            gw_payload = {
                "accountId": clean_account,
                "merchantName": clean_name,
                "merchantCity": clean_city,
                "amount": float(amount),
                "currency": curr_upper,
                "billNumber": bill_no,
                "storeLabel": "Telegram Bot"
            }
            r = requests.post(f"{base_gw}/api/v1/khqr/generate", json=gw_payload, headers=DEFAULT_HEADERS, timeout=6)
            if r.status_code == 200:
                data = r.json()
                qr_str = data.get("qrString") or data.get("qr")
                md5_str = data.get("md5")
                if qr_str and md5_str:
                    return {
                        "qr": qr_str,
                        "md5": md5_str,
                        "deeplink": data.get("deeplink") or generate_deeplink(qr_str),
                        "billNumber": bill_no,
                        "source": "gateway"
                    }
        except Exception:
            pass
        raise RuntimeError(f"KHQR generation failed: {e}")

def create_khqr_card(qr_string: str, amount_str: str, merchant_name: str, account_id: str) -> io.BytesIO:
    """
    Renders a branded KHQR card with red banner, QR code, merchant name, and amount.
    """
    if not QRCODE_AVAILABLE or qrcode is None or Image is None:
        raise RuntimeError("qrcode and Pillow are required to generate KHQR card images. Please ensure requirements.txt is installed.")

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
