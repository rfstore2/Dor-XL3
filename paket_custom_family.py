import json
import shutil
import textwrap
from api_request import send_api_request, get_family
from auth_helper import AuthInstance
from ui import clear_screen, pause, show_package_details


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

def get_packages_by_family(family_code: str, is_enterprise: bool = False):
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        print("No active user tokens found.")
        pause()
        return None

    packages = []

    data = get_family(api_key, tokens, family_code, is_enterprise)
    if not data:
        print("Failed to load family data.")
        pause()
        return None

    in_package_menu = True
    while in_package_menu:
        clear_screen()
        table_width = shutil.get_terminal_size((100, 20)).columns

        family_name = data['package_family']["name"]
        print(render_table(f"FAMILY NAME: {family_name}", [], show_headers=False, width=table_width, aligns=None))

        package_variants = data["package_variants"]
        option_number = 1
        variant_number = 1

        for variant in package_variants:
            variant_name = variant["name"]
            print(render_table(f"Variant {variant_number}: {variant_name}", [], show_headers=False, width=table_width))

            variant_table = []
            for option in variant["package_options"]:
                option_name = option["name"]
                price = option["price"]
                code = option["package_option_code"]

                variant_table.append([option_number, option_name, f"Rp {price}"])

                packages.append({
                    "number": option_number,
                    "name": option_name,
                    "price": price,
                    "code": code
                })

                option_number += 1

            if variant_table:
                print(render_table("PAKET", variant_table,
                                   headers=["No", "Nama Paket", "Harga"], width=table_width, aligns=["center", "left", "left"]))

            variant_number += 1

        # Menu kembali
        print(render_table("KEMBALI", [["00 Kembali ke menu sebelumnya"]],
                           show_headers=False, width=table_width))

        pkg_choice = input("Pilih paket (nomor): ").strip()
        if pkg_choice == "00":
            in_package_menu = False
            return None

        if not pkg_choice.isdigit():
            print("Input tidak valid. Silakan masukkan nomor yang benar.")
            pause()
            continue

        selected_pkg = next((p for p in packages if p["number"] == int(pkg_choice)), None)
        if not selected_pkg:
            print("Paket tidak ditemukan. Silakan masukkan nomor yang benar.")
            pause()
            continue

        is_done = show_package_details(api_key, tokens, selected_pkg["code"])
        if is_done:
            in_package_menu = False
            return None

    return packages
