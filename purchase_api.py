from datetime import datetime, timezone, timedelta
import json
import uuid
import base64
import qrcode
import shutil 
from PIL import Image


import requests
from api_request import *
from crypto_helper import API_KEY, build_encrypted_field, decrypt_xdata, encryptsign_xdata, java_like_timestamp, get_x_signature_payment, get_x_signature_bounty
import time
import io

BASE_API_URL = os.getenv("BASE_API_URL")
AX_DEVICE_ID = os.getenv("AX_DEVICE_ID")
AX_FP = os.getenv("AX_FP")
UA = os.getenv("UA")

def get_terminal_width(default=80):
    """Mengembalikan lebar terminal, jika gagal gunakan default."""
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return default
        
def render_table(title, rows, headers=None, width=None, show_headers=False, aligns=None):
    if width is None:
        width = get_terminal_width()

    # Tentukan jumlah kolom
    if headers:
        n_cols = len(headers)
    elif rows:
        n_cols = len(rows[0])
    else:
        n_cols = 1

    # Lebar kolom awal
    no_col_width = 6 if headers and "No" in headers else None
    col_sizes = []

    if no_col_width:
        flexible_cols = n_cols - 1
        remaining_width = width - (n_cols * 3 + 1) - no_col_width
        col_width = remaining_width // flexible_cols if flexible_cols > 0 else remaining_width
        for i in range(n_cols):
            if headers and headers[i] == "No":
                col_sizes.append(no_col_width)
            else:
                col_sizes.append(col_width)
    else:
        remaining_width = width - (n_cols * 3 + 1)
        col_width = remaining_width // n_cols
        col_sizes = [col_width] * n_cols

    # Sesuaikan lebar kolom agar muat konten & header
    if headers:
        for i, h in enumerate(headers):
            max_len = max(len(str(r[i])) for r in rows) if rows else 0
            needed = max(len(h), max_len)
            if needed > col_sizes[i]:
                col_sizes[i] = needed

    # Alignment isi tabel
    if aligns is None:
        aligns = []
        if headers:
            for h in headers:
                if "No" in str(h):
                    aligns.append("center")
                elif "Harga" in str(h):
                    aligns.append("left")
                else:
                    aligns.append("left")
        else:
            aligns = ["center"] * n_cols
    else:
        # Sanitasi input aligns supaya panjangnya sama dengan jumlah kolom
        norm = []
        for a in aligns:
            a_s = str(a).lower()
            if a_s.startswith("l"):
                norm.append("left")
            elif a_s.startswith("r"):
                norm.append("right")
            elif a_s.startswith("c"):
                norm.append("center")
            else:
                norm.append("left")
        if len(norm) < n_cols:
            norm.extend(["left"] * (n_cols - len(norm)))
        elif len(norm) > n_cols:
            norm = norm[:n_cols]
        aligns = norm

    def fmt_cell(text, size, align="center"):
        text = str(text)
        if len(text) > size:
            text = text[:max(0, size - 1)] + "…"  # truncate kalau terlalu panjang
        if align == "left":
            return text.ljust(size)
        elif align == "right":
            return text.rjust(size)
        return text.center(size)

    # Border builder
    def make_border(char="-"):
        return "+" + "+".join(char * (w + 2) for w in col_sizes) + "+"

    total_width = sum(col_sizes) + 3 * n_cols - 1
    full_border = "+" + "-" * total_width + "+"

    lines = []
    # Judul
    lines.append(full_border)
    lines.append("|" + title.center(total_width) + "|")
    lines.append(full_border)

    # Header
    if headers and show_headers:
        header_row = "|" + "|".join(
            " " + fmt_cell(headers[i], col_sizes[i], "center") + " "
            for i in range(n_cols)
        ) + "|"
        lines.append(make_border("-"))
        lines.append(header_row)
        lines.append(make_border("-"))

    # Isi
    for row in rows:
        row_line = "|" + "|".join(
            " " + fmt_cell(row[i], col_sizes[i], aligns[i]) + " "
            for i in range(n_cols)
        ) + "|"
        lines.append(row_line)

    lines.append(full_border)
    return "\n".join(lines)


def get_payment_methods(
    api_key: str,
    tokens: dict,
    token_confirmation: str,
    payment_target: str,
):
    payment_path = "payments/api/v8/payment-methods-option"
    payment_payload = {
        "payment_type": "PURCHASE",
        "is_enterprise": False,
        "payment_target": payment_target,
        "lang": "en",
        "is_referral": False,
        "token_confirmation": token_confirmation
    }
    
    payment_res = send_api_request(api_key, payment_path, payment_payload, tokens["id_token"], "POST")
    if payment_res["status"] != "SUCCESS":
        print("Failed to fetch payment methods.")
        print(f"Error: {payment_res}")
        return None
    
    
    
    return payment_res["data"]

def settlement_multipayment(
    api_key: str,
    tokens: dict,
    token_payment: str,
    ts_to_sign: int,
    payment_target: str,
    price: int,
    amount_int: int,
    wallet_number: str,
    item_name: str = "",
    payment_method: str = "DANA"
):
    # Settlement request
    path = "payments/api/v8/settlement-multipayment/ewallet"
    settlement_payload = {
        "akrab": {
            "akrab_members": [],
            "akrab_parent_alias": "",
            "members": []
        },
        "can_trigger_rating": False,
        "total_discount": 0,
        "coupon": "",
        "payment_for": "BUY_PACKAGE",
        "topup_number": "",
        "is_enterprise": False,
        "autobuy": {
            "is_using_autobuy": False,
            "activated_autobuy_code": "",
            "autobuy_threshold_setting": {
            "label": "",
            "type": "",
            "value": 0
            }
        },
        "cc_payment_type": "",
        "access_token": tokens["access_token"],
        "is_myxl_wallet": False,
        "wallet_number": wallet_number,
        "additional_data": {
            "original_price": price,
            "is_spend_limit_temporary": False,
            "migration_type": "",
            "spend_limit_amount": 0,
            "is_spend_limit": False,
            "tax": 0,
            "benefit_type": "",
            "quota_bonus": 0,
            "cashtag": "",
            "is_family_plan": False,
            "combo_details": [],
            "is_switch_plan": False,
            "discount_recurring": 0,
            "has_bonus": False,
            "discount_promo": 0
        },
        "total_amount": amount_int,
        "total_fee": 0,
        "is_use_point": False,
        "lang": "en",
        "items": [{
            "item_code": payment_target,
            "product_type": "",
            "item_price": price,
            "item_name": item_name,
            "tax": 0
        }],
        "verification_token": token_payment,
        "payment_method": payment_method,
        "timestamp": int(time.time())
    }
    
    encrypted_payload = encryptsign_xdata(
        api_key=api_key,
        method="POST",
        path=path,
        id_token=tokens["id_token"],
        payload=settlement_payload
    )
    
    xtime = int(encrypted_payload["encrypted_body"]["xtime"])
    sig_time_sec = (xtime // 1000)
    x_requested_at = datetime.fromtimestamp(sig_time_sec, tz=timezone.utc).astimezone()
    settlement_payload["timestamp"] = ts_to_sign
    
    body = encrypted_payload["encrypted_body"]
    x_sig = get_x_signature_payment(
            api_key,
            tokens["access_token"],
            ts_to_sign,
            payment_target,
            token_payment,
            payment_method
        )
    
    headers = {
        "host": BASE_API_URL.replace("https://", ""),
        "content-type": "application/json; charset=utf-8",
        "user-agent": UA,
        "x-api-key": API_KEY,
        "authorization": f"Bearer {tokens['id_token']}",
        "x-hv": "v3",
        "x-signature-time": str(sig_time_sec),
        "x-signature": x_sig,
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": java_like_timestamp(x_requested_at),
        "x-version-app": "8.6.0",
    }
    
    url = f"{BASE_API_URL}/{path}"
    print("Sending settlement request...")
    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
    
    try:
        decrypted_body = decrypt_xdata(api_key, json.loads(resp.text))
        return decrypted_body
    except Exception as e:
        print("[decrypt err]", e)
        return resp.text

def show_multipayment(api_key: str, tokens: dict, package_option_code: str, token_confirmation: str, price: int, item_name: str = ""):
    print("Fetching available payment methods...")
    
    payment_methods_data = get_payment_methods(
        api_key=api_key,
        tokens=tokens,
        token_confirmation=token_confirmation,
        payment_target=package_option_code,
    )
    
    token_payment = payment_methods_data["token_payment"]
    ts_to_sign = payment_methods_data["timestamp"]
    
    amount_str = input(f"Total amount is {price}.\nEnter value if you need to overwrite, press enter to ignore & use default amount: ")
    amount_int = price
    
    if amount_str != "":
        try:
            amount_int = int(amount_str)
        except ValueError:
            print("Invalid overwrite input, using original price.")
            return None
    
    choosing_payment_method = True
    while choosing_payment_method:
        payment_method = ""
        wallet_number = ""
        payment_options = [
            ["1", "DANA"],
            ["2", "ShopeePay"],
            ["3", "GoPay"],
            ["4", "OVO"]
        ]

# Tampilkan tabel metode pembayaran
        print(render_table(
            "METODE PEMBAYARAN",
            payment_options,
            headers=["No", "Metode"],
            show_headers=True,
            aligns=["center", "left"]  # No di tengah, Metode kiri
        ))
        choice = input("Pilih metode pembayaran: ")
        if choice == "1":
            payment_method = "DANA"
            wallet_number = input("Masukkan nomor DANA (contoh: 08123456789): ")
            # Validate number format
            if not wallet_number.startswith("08") or not wallet_number.isdigit() or len(wallet_number) < 10 or len(wallet_number) > 13:
                print("Nomor DANA tidak valid. Pastikan nomor diawali dengan '08' dan memiliki panjang yang benar.")
                continue
            choosing_payment_method = False
        elif choice == "2":
            payment_method = "SHOPEEPAY"
            choosing_payment_method = False
        elif choice == "3":
            payment_method = "GOPAY"
            choosing_payment_method = False
        elif choice == "4":
            payment_method = "OVO"
            wallet_number = input("Masukkan nomor OVO (contoh: 08123456789): ")
            # Validate number format
            if not wallet_number.startswith("08") or not wallet_number.isdigit() or len(wallet_number) < 10 or len(wallet_number) > 13:
                print("Nomor OVO tidak valid. Pastikan nomor diawali dengan '08' dan memiliki panjang yang benar.")
                continue
            choosing_payment_method = False
        else:
            print("Pilihan tidak valid.")
            continue
    
    settlement_response = settlement_multipayment(
        api_key,
        tokens,
        token_payment,
        ts_to_sign,
        package_option_code,
        price,
        amount_int,
        wallet_number,
        item_name,
        payment_method
    )
    
    # print(f"Settlement response: {json.dumps(settlement_response, indent=2)}")
    if settlement_response["status"] != "SUCCESS":
        print("Failed to initiate settlement.")
        print(f"Error: {settlement_response}")
        return
    
    if payment_method != "OVO":
        deeplink = settlement_response["data"].get("deeplink", "")
        if deeplink:
            print(f"Silahkan selesaikan pembayaran melalui link berikut:\n{deeplink}")
    else:
        print("Silahkan buka aplikasi OVO Anda untuk menyelesaikan pembayaran.")
    return

def settlement_qris(
    api_key: str,
    tokens: dict,
    token_payment: str,
    ts_to_sign: int,
    payment_target: str,
    price: int,
    item_name: str = "",
):  
    amount_str = input(f"Total amount is {price}.\nEnter value if you need to overwrite, press enter to ignore & use default amount: ")
    amount_int = price
    
    if amount_str != "":
        try:
            amount_int = int(amount_str)
        except ValueError:
            print("Invalid overwrite input, using original price.")
            return None
    
    # Settlement request
    path = "payments/api/v8/settlement-multipayment/qris"
    settlement_payload = {
        "akrab": {
            "akrab_members": [],
            "akrab_parent_alias": "",
            "members": []
        },
        "can_trigger_rating": False,
        "total_discount": 0,
        "coupon": "",
        "payment_for": "BUY_PACKAGE",
        "topup_number": "",
        "is_enterprise": False,
        "autobuy": {
            "is_using_autobuy": False,
            "activated_autobuy_code": "",
            "autobuy_threshold_setting": {
            "label": "",
            "type": "",
            "value": 0
            }
        },
        "access_token": tokens["access_token"],
        "is_myxl_wallet": False,
        "additional_data": {
            "original_price": price,
            "is_spend_limit_temporary": False,
            "migration_type": "",
            "spend_limit_amount": 0,
            "is_spend_limit": False,
            "tax": 0,
            "benefit_type": "",
            "quota_bonus": 0,
            "cashtag": "",
            "is_family_plan": False,
            "combo_details": [],
            "is_switch_plan": False,
            "discount_recurring": 0,
            "has_bonus": False,
            "discount_promo": 0
        },
        "total_amount": amount_int,
        "total_fee": 0,
        "is_use_point": False,
        "lang": "en",
        "items": [{
            "item_code": payment_target,
            "product_type": "",
            "item_price": price,
            "item_name": item_name,
            "tax": 0
        }],
        "verification_token": token_payment,
        "payment_method": "QRIS",
        "timestamp": int(time.time())
    }
    
    encrypted_payload = encryptsign_xdata(
        api_key=api_key,
        method="POST",
        path=path,
        id_token=tokens["id_token"],
        payload=settlement_payload
    )
    
    xtime = int(encrypted_payload["encrypted_body"]["xtime"])
    sig_time_sec = (xtime // 1000)
    x_requested_at = datetime.fromtimestamp(sig_time_sec, tz=timezone.utc).astimezone()
    settlement_payload["timestamp"] = ts_to_sign
    
    body = encrypted_payload["encrypted_body"]
    x_sig = get_x_signature_payment(
            api_key,
            tokens["access_token"],
            ts_to_sign,
            payment_target,
            token_payment,
            "QRIS"
        )
    
    headers = {
        "host": BASE_API_URL.replace("https://", ""),
        "content-type": "application/json; charset=utf-8",
        "user-agent": UA,
        "x-api-key": API_KEY,
        "authorization": f"Bearer {tokens['id_token']}",
        "x-hv": "v3",
        "x-signature-time": str(sig_time_sec),
        "x-signature": x_sig,
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": java_like_timestamp(x_requested_at),
        "x-version-app": "8.6.0",
    }
    
    url = f"{BASE_API_URL}/{path}"
    print("Sending settlement request...")
    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
    
    try:
        decrypted_body = decrypt_xdata(api_key, json.loads(resp.text))
        if decrypted_body["status"] != "SUCCESS":
            print("Failed to initiate settlement.")
            print(f"Error: {decrypted_body}")
            return None
        
        transaction_id = decrypted_body["data"]["transaction_code"]
        
        return transaction_id
    except Exception as e:
        print("[decrypt err]", e)
        return resp.text
    
def get_qris_code(
    api_key: str,
    tokens: dict,
    transaction_id: str
):
    path = "payments/api/v8/pending-detail"
    payload = {
        "transaction_id": transaction_id,
        "is_enterprise": False,
        "lang": "en",
        "status": ""
    }
    
    res = send_api_request(api_key, path, payload, tokens["id_token"], "POST")
    if res["status"] != "SUCCESS":
        print("Failed to fetch QRIS code.")
        print(f"Error: {res}")
        return None
    
    return res["data"]["qr_code"]

def show_qris_payment(api_key: str, tokens: dict, package_option_code: str, token_confirmation: str, price: int, item_name: str = ""):
    print("Fetching payment method details...")
    
    # Ambil data payment method
    payment_methods_data = get_payment_methods(
        api_key=api_key,
        tokens=tokens,
        token_confirmation=token_confirmation,
        payment_target=package_option_code,
    )
    
    token_payment = payment_methods_data["token_payment"]
    ts_to_sign = payment_methods_data["timestamp"]
    
    # Buat QRIS transaction
    transaction_id = settlement_qris(
        api_key,
        tokens,
        token_payment,
        ts_to_sign,
        package_option_code,
        price,
        item_name
    )
    
    if not transaction_id:
        print("Failed to create QRIS transaction.")
        return
    
    print("Fetching QRIS code...")
    qris_code = get_qris_code(api_key, tokens, transaction_id)
    if not qris_code:
        print("Failed to get QRIS code.")
        return
    
    # Simpan QR sebagai PNG
    qr_img = qrcode.make(qris_code)
    qr_img.save("qris.png")
    print("QR Code berhasil dibuat dan disimpan sebagai 'qris.png'")

    # Tampilkan QR ASCII di tengah tabel terminal
    terminal_width = shutil.get_terminal_size((80, 20)).columns
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=1
    )
    qr.add_data(qris_code)
    qr.make(fit=True)

    # Tangkap output QR ASCII ke StringIO
    output = io.StringIO()
    qr.print_ascii(out=output, invert=True)
    qr_ascii_lines = output.getvalue().splitlines()

    print("+" + "-"*(terminal_width-2) + "+")
    for line in qr_ascii_lines:
        print("|" + line.center(terminal_width-2) + "|")
    print("+" + "-"*(terminal_width-2) + "+")

    # Tampilkan link QRIS sebagai alternatif
    qris_b64 = base64.urlsafe_b64encode(qris_code.encode()).decode()
    qris_url = f"https://ki-ar-kod.netlify.app/?data={qris_b64}"
    print(f"\nAtau buka link berikut untuk melihat QRIS:\n{qris_url}\n")
    return
def settlement_bounty(
    api_key: str,
    tokens: dict,
    token_confirmation: str,
    ts_to_sign: int,
    payment_target: str,
    price: int,
    item_name: str = "",
):
    # Settlement request
    path = "api/v8/personalization/bounties-exchange"
    settlement_payload = {
        "total_discount": 0,
        "is_enterprise": False,
        "payment_token": "",
        "token_payment": "",
        "activated_autobuy_code": "",
        "cc_payment_type": "",
        "is_myxl_wallet": False,
        "pin": "",
        "ewallet_promo_id": "",
        "members": [],
        "total_fee": 0,
        "fingerprint": "",
        "autobuy_threshold_setting": {
            "label": "",
            "type": "",
            "value": 0
        },
        "is_use_point": False,
        "lang": "en",
        "payment_method": "BALANCE",
        "timestamp": ts_to_sign,
        "points_gained": 0,
        "can_trigger_rating": False,
        "akrab_members": [],
        "akrab_parent_alias": "",
        "referral_unique_code": "",
        "coupon": "",
        "payment_for": "REDEEM_VOUCHER",
        "with_upsell": False,
        "topup_number": "",
        "stage_token": "",
        "authentication_id": "",
        "encrypted_payment_token": build_encrypted_field(urlsafe_b64=True),
        "token": "",
        "token_confirmation": token_confirmation,
        "access_token": tokens["access_token"],
        "wallet_number": "",
        "encrypted_authentication_id": build_encrypted_field(urlsafe_b64=True),
        "additional_data": {
            "original_price": 0,
            "is_spend_limit_temporary": False,
            "migration_type": "",
            "akrab_m2m_group_id": "",
            "spend_limit_amount": 0,
            "is_spend_limit": False,
            "mission_id": "",
            "tax": 0,
            "benefit_type": "",
            "quota_bonus": 0,
            "cashtag": "",
            "is_family_plan": False,
            "combo_details": [],
            "is_switch_plan": False,
            "discount_recurring": 0,
            "is_akrab_m2m": False,
            "balance_type": "",
            "has_bonus": False,
            "discount_promo": 0
        },
        "total_amount": 0,
        "is_using_autobuy": False,
        "items": [{
            "item_code": payment_target,
            "product_type": "",
            "item_price": price,
            "item_name": item_name,
            "tax": 0
        }]
    }
        
    encrypted_payload = encryptsign_xdata(
        api_key=api_key,
        method="POST",
        path=path,
        id_token=tokens["id_token"],
        payload=settlement_payload
    )
    
    xtime = int(encrypted_payload["encrypted_body"]["xtime"])
    sig_time_sec = (xtime // 1000)
    x_requested_at = datetime.fromtimestamp(sig_time_sec, tz=timezone.utc).astimezone()
    settlement_payload["timestamp"] = ts_to_sign
    
    body = encrypted_payload["encrypted_body"]
        
    x_sig = get_x_signature_bounty(
        api_key=api_key,
        access_token=tokens["access_token"],
        sig_time_sec=ts_to_sign,
        package_code=payment_target,
        token_payment=token_confirmation
    )
    
    headers = {
        "host": BASE_API_URL.replace("https://", ""),
        "content-type": "application/json; charset=utf-8",
        "user-agent": UA,
        "x-api-key": API_KEY,
        "authorization": f"Bearer {tokens['id_token']}",
        "x-hv": "v3",
        "x-signature-time": str(sig_time_sec),
        "x-signature": x_sig,
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": java_like_timestamp(x_requested_at),
        "x-version-app": "8.6.0",
    }
    
    url = f"{BASE_API_URL}/{path}"
    print("Sending bounty request...")
    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
    
    try:
        decrypted_body = decrypt_xdata(api_key, json.loads(resp.text))
        if decrypted_body["status"] != "SUCCESS":
            print("Failed to claim bounty.")
            print(f"Error: {decrypted_body}")
            return None
        
        print(decrypted_body)
        
        return decrypted_body
    except Exception as e:
        print("[decrypt err]", e)
        return resp.text
