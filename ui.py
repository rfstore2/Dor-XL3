import json
import os
import sys
import banner
import textwrap
import shutil
from datetime import datetime
import io

from api_request import get_otp, submit_otp, save_tokens, get_package, purchase_package, get_addons
from purchase_api import show_multipayment, show_qris_payment, settlement_bounty
from auth_helper import AuthInstance
from util import display_html

ascii_art = banner.load("https://d17e22l2uh4h4n.cloudfront.net/corpweb/pub-xlaxiata/2019-03/xl-logo.png", globals())

TABLE_WIDTH = 100  # Default table width

max_col_width = TABLE_WIDTH - 5
# -----------------------------
# Utils
# -----------------------------
def get_terminal_width(default=80):
    try:
        return shutil.get_terminal_size().columns
    except:
        return default


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def show_banner():
    # Dapatkan lebar terminal
    term_width = shutil.get_terminal_size().columns

    # Tangkap output ascii_art.to_terminal
    buffer = io.StringIO()
    sys.stdout = buffer
    ascii_art.to_terminal(columns=60)  # tetap pakai kode dasar
    sys.stdout = sys.__stdout__

    # Ambil setiap baris dan center
    for line in buffer.getvalue().splitlines():
        print(line.center(term_width))


def pause():
    input("\nTekan Enter untuk lanjut...")


# -----------------------------
# Table rendering
# -----------------------------
# -----------------------------
# Table rendering (patched)
# -----------------------------
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

# -----------------------------
# Helper Functions
# -----------------------------
def format_unit(total, name=""):
    if "Call" in name:
        return f"{total / 60:.2f} menit"
    elif total >= 1_000_000_000:
        return f"{total / (1024**3):.2f} GB"
    elif total >= 1_000_000:
        return f"{total / (1024**2):.2f} MB"
    elif total >= 1_000:
        return f"{total / 1024:.2f} KB"
    return str(total)


# -----------------------------
# UI Functions
# -----------------------------
def show_main_menu(number, balance, balance_expired_at):
    clear_screen()
    show_banner()
    expired_at_dt = datetime.fromtimestamp(balance_expired_at).strftime("%Y-%m-%d %H:%M:%S")

    account_info = [
        ["Nomor", number],
        ["Pulsa", f"Rp {balance}"],
        ["Masa Aktif", expired_at_dt],
    ]

    menu_options = [
        ["1", "Login/Ganti akun"],
        ["2", "Lihat Paket Saya"],
        ["3", "Beli Paket XUT"],
        ["4", "Beli Paket Berdasarkan Family Code"],
        ["5", "Beli Paket Berdasarkan Family Code (Enterprise)"],
        ["6", "List Family Code"],
        ["99", "Tutup aplikasi"],
    ]

    # Info akun: tetap dua kolom, rata kiri
    print(render_table(
        "INFORMASI AKUN",
        account_info,
        headers=["Keterangan", "Nilai"],
        show_headers=True
    ))

    # Menu utama: pakai header dengan kolom No (fixed max 4 digit)
    print(render_table(
        "MAIN MENU",
        menu_options,
        headers=["No", "Keterangan"],
        show_headers=True
    ))


def show_account_menu():
    clear_screen()
    AuthInstance.load_tokens()
    users = AuthInstance.refresh_tokens
    active_user = AuthInstance.get_active_user()

    in_account_menu = True
    add_user = False
    while in_account_menu:
        clear_screen()
        show_banner()
        if active_user is None or add_user:
            number, refresh_token = login_prompt(AuthInstance.api_key)
            if not refresh_token:
                print("Gagal menambah akun. Silahkan coba lagi.")
                pause()
                continue
            AuthInstance.add_refresh_token(str(number), refresh_token)
            AuthInstance.load_tokens()
            users = AuthInstance.refresh_tokens
            add_user = False
            active_user = AuthInstance.get_active_user()
            continue

        # Tabel akun tersimpan
        if not users:
            print(render_table(
                "AKUN TERSIMPAN",
                [["-", "Tidak ada akun tersimpan"]],
                headers=["No", "Nomor HP"],
                show_headers=True,
                aligns=["center", "left"]
            ))
        else:
            table_data = []
            for idx, user in enumerate(users):
                is_active = active_user and str(user["number"]) == str(active_user["number"])
                marker = " (Aktif)" if is_active else ""
                table_data.append([str(idx + 1), str(user["number"]) + marker])
            print(render_table(
                "AKUN TERSIMPAN",
                table_data,
                headers=["No", "Nomor HP"],
                show_headers=True,
                aligns=["center", "left"]
            ))

        # Commands
        commands = [
            ["0", "Tambah Akun"],
            ["00", "Kembali ke menu utama"],
            ["99", "Hapus Akun aktif"],
        ]
        print(render_table(
            "COMMANDS",
            commands,
            headers=["No", "Keterangan"],
            show_headers=True
        ))

        input_str = input("Pilihan: ")
        if input_str == "00":
            return str(active_user["number"]) if active_user else None
        elif input_str == "0":
            add_user = True
            continue
        elif input_str == "99":
            if not active_user:
                print("Tidak ada akun aktif untuk dihapus.")
                pause()
                continue
            confirm = input(f"Yakin ingin menghapus akun {active_user['number']}? (y/n): ")
            if confirm.lower() == "y":
                AuthInstance.remove_refresh_token(str(active_user["number"]))
                users = AuthInstance.refresh_tokens
                active_user = AuthInstance.get_active_user()
                print("Akun berhasil dihapus.")
                pause()
            else:
                print("Penghapusan akun dibatalkan.")
                pause()
            continue
        elif input_str.isdigit() and 1 <= int(input_str) <= len(users):
            selected_user = users[int(input_str) - 1]
            return str(selected_user["number"])
        else:
            print("Input tidak valid. Silahkan coba lagi.")
            pause()


def login_prompt(api_key: str):
    clear_screen()
    show_banner()
    print(render_table("LOGIN KE MYXL", [["-", ""]]))
    phone_number = input("Masukan nomor XL Prabayar (Contoh 6281234567890): ")

    if not phone_number.startswith("628") or not (10 <= len(phone_number) <= 14):
        print("Nomor tidak valid.")
        return None, None

    try:
        subscriber_id = get_otp(phone_number)
        if not subscriber_id:
            return None, None
        print("OTP Berhasil dikirim ke nomor Anda.")
        otp = input("Masukkan OTP yang telah dikirim: ")
        if not otp.isdigit() or len(otp) != 6:
            print("OTP tidak valid.")
            pause()
            return None, None
        tokens = submit_otp(api_key, phone_number, otp)
        if not tokens:
            print("Gagal login. Periksa OTP dan coba lagi.")
            pause()
            return None, None
        print("Berhasil login!")
        return phone_number, tokens["refresh_token"]
    except Exception:
        return None, None


def show_package_menu(packages):
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        print(render_table("ERROR", [["No active user tokens found"]], show_headers=False))
        pause()
        return None

    while True:
        clear_screen()
        show_banner()

        # Data tabel: No, Nama Paket, Harga
        table_data = [
            [pkg["number"], pkg["name"], f"Rp {pkg['price']}"]
            for pkg in packages
        ]

        # Tabel paket tersedia
        print(render_table(
            "PAKET TERSEDIA",
            table_data,
            headers=["No", "Nama Paket", "Harga"],
            show_headers=True
        ))

        # Tabel kembali
        print(render_table(
            "KEMBALI",
            [["99 Kembali ke menu utama"]],
            headers=["Keterangan"],
            show_headers=False
        ))

        pkg_choice = input("Pilih paket (nomor): ").strip()
        if pkg_choice == "99":
            return None

        if not pkg_choice.isdigit():
            print("Input tidak valid. Silakan masukan nomor yang benar.")
            pause()
            continue

        selected_pkg = next((p for p in packages if p["number"] == int(pkg_choice)), None)
        if not selected_pkg:
            print("Paket tidak ditemukan. Silakan masukan nomor yang benar.")
            pause()
            continue

        is_done = show_package_details(api_key, tokens, selected_pkg["code"])
        if is_done:
            return None

def show_package_details(api_key, tokens, package_option_code):
    clear_screen()
    show_banner()
    package = get_package(api_key, tokens, package_option_code)
    if not package:
        print("Failed to load package details.")
        pause()
        return False

    name1 = package.get("package_family", {}).get("name", "")
    name2 = package.get("package_detail_variant", {}).get("name", "")
    name3 = package.get("package_option", {}).get("name", "")
    title = f"{name1} {name2} {name3}".strip()

    price = package["package_option"]["price"]
    validity = package["package_option"]["validity"]
    benefits = package["package_option"]["benefits"]
    detail = display_html(package["package_option"]["tnc"])

    package_table = [
    ["Nama Paket", title],
    ["Harga", f"Rp {price}"],
    ["Masa Aktif", validity]
    ]

    print(render_table(
         "DETAIL PAKET",
        package_table,
        headers=["Keterangan", "Value"],  # optional, bisa dipakai atau tidak
        show_headers=False,
        aligns=["left", "left"]          # kiri semua
    ))
    if benefits:
        benefit_table = [[b["name"], format_unit(b["total"], b["name"])] for b in benefits]
        print(render_table(
        "BENEFITS", 
        benefit_table,
        headers=["Keterangan", "Value"],  # optional, bisa dipakai atau tidak
        show_headers=False,
        aligns=["left", "left"]        
        ))
        
    try:
        addons = get_addons(api_key, tokens, package_option_code)
        addons_list = []

        if isinstance(addons, dict):
            addons_list = addons.get("data", [])
        elif isinstance(addons, list):
            addons_list = addons

        if addons_list:
            # Tampilkan tabel normal jika ada addons
            rows = []
            for addon in addons_list:
                if isinstance(addon, dict):
                    name = addon.get("name", "-")
                    price = f"Rp {addon.get('price',0)}"
                else:
                    name = str(addon)
                    price = "-"
                rows.append([name, price])

            print(render_table(
                "ADDONS",
                rows,
                headers=["Nama Addon", "Harga"],
                show_headers=True,
                aligns=["left", "left"]
            ))

        else:
        # Jika kosong, tampilkan JSON dalam tabel full box
            json_str = json.dumps(addons, indent=2)
            json_lines = json_str.splitlines()
        # Buat list of lists agar render_table bisa pakai
            addon_rows = [[line] for line in json_lines]

            print(render_table(
                "ADDONS",
                addon_rows,
                headers=["Keterangan"],
                show_headers=False,
                aligns=["left"]
            ))

    except Exception as e:
        print(f"Fetching addons failed: {e}")


    # Split menjadi baris
    detail_lines = []
    for paragraph in detail.splitlines():
        wrapped = textwrap.wrap(paragraph, width=max_col_width)
        if not wrapped:
            detail_lines.append("")  # baris kosong
        else:
            detail_lines.extend(wrapped)
    # Ubah menjadi list of lists agar render_table bisa pakai
    detail_rows = [[line] for line in detail_lines if line.strip()]

# Tampilkan tabel
    print(render_table(
        "SYARAT & KETENTUAN",
        detail_rows,
        headers=["Keterangan"],
        show_headers=False,
        aligns=["left"]
    ))

    payment_for = package["package_family"]["payment_for"]
    payment_methods = [
        ["1", "Beli dengan Pulsa"],
        ["2", "Beli dengan E-Wallet"],
        ["3", "Bayar dengan QRIS"],
    ]
    if payment_for == "REDEEM_VOUCHER":
        payment_methods.append(["4", "Ambil sebagai bonus (jika tersedia)"])
    print(render_table(
    "METODE PEMBAYARAN", 
    payment_methods,
    headers=["No", "Value"],  # optional, bisa dipakai atau tidak
        show_headers=False,
        aligns=["center", "left"]        
    ))

    choice = input("Pilih metode pembayaran: ")
    token_confirmation = package["token_confirmation"]
    ts_to_sign = package["timestamp"]
    item_name = f"{name2} {name3}".strip()

    try:
        if choice == "1":
            purchase_package(api_key, tokens, package_option_code)
            input("Silahkan cek hasil pembelian di aplikasi MyXL. Tekan Enter untuk kembali.")
            return True
        elif choice == "2":
            show_multipayment(api_key, tokens, package_option_code, token_confirmation, price, item_name)
            input("Silahkan lakukan pembayaran & cek hasil pembelian di aplikasi MyXL. Tekan Enter untuk kembali.")
            return True
        elif choice == "3":
            try:
                show_qris_payment(api_key, tokens, package_option_code, token_confirmation, price, item_name)
                input("Silahkan lakukan pembayaran & cek hasil pembelian di aplikasi MyXL. Tekan Enter untuk kembali.")
            except Exception as e:
                print(f"QRIS payment failed: {e}")
                pause()
            return True
        elif choice == "4" and payment_for == "REDEEM_VOUCHER":
            try:
                settlement_bounty(api_key=api_key, tokens=tokens, token_confirmation=token_confirmation, ts_to_sign=ts_to_sign, payment_target=package_option_code, price=price, item_name=item_name)
                input("Bonus berhasil diambil. Tekan Enter untuk kembali.")
            except Exception as e:
                print(f"Redeem voucher failed: {e}")
                pause()
            return True
        else:
            print("Purchase cancelled.")
            pause()
            return False
    except Exception as e:
        print(f"An unexpected error occurred during purchase: {e}")
        pause()
        return False
