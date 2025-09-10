import json
import shutil
import textwrap
from api_request import send_api_request, get_family
from auth_helper import AuthInstance
from ui import pause, clear_screen


PACKAGE_FAMILY_CODE = "08a3b1e6-8e78-4e45-a540-b40f06871cfe"


def render_table(title, rows, headers=None, show_headers=True, width=None):
    term_width = shutil.get_terminal_size((100, 20)).columns
    if width is None or width > term_width:
        width = term_width

    if headers:
        col_no = 6
        col_price = 20
        col_name = width - (col_no + col_price + 7)
    else:
        col_name = width - 4
        col_no = col_price = 0

    def fmt(text, col_width, align="left"):
        text = str(text)
        if align == "center":
            return text.center(col_width)
        elif align == "right":
            return text.rjust(col_width)
        return text.ljust(col_width)

    lines = []
    lines.append("+" + "-" * (width - 2) + "+")
    lines.append("|" + title.center(width - 2) + "|")
    lines.append("+" + "-" * (width - 2) + "+")

    if headers and show_headers:
        header_line = (
            f"| {fmt(headers[0], col_no, 'center')} "
            f"| {fmt(headers[1], col_name, 'center')} "
            f"| {fmt(headers[2], col_price, 'center')} |"
        )
        lines.append(header_line)
        lines.append("+" + "-" * (width - 2) + "+")

    for row in rows:
        if headers:
            no, nama, harga = row
            wrapped_nama = textwrap.wrap(str(nama), col_name) or [""]
            wrapped_no = [str(no).rjust(col_no)] + [""] * (len(wrapped_nama) - 1)
            wrapped_harga = [str(harga).rjust(col_price)] + [""] * (len(wrapped_nama) - 1)

            for n, nm, h in zip(wrapped_no, wrapped_nama, wrapped_harga):
                line = (
                    f"| {fmt(n, col_no, 'right')}"
                    f" | {fmt(nm, col_name, 'left')}"
                    f" | {fmt(h, col_price, 'right')} |"
                )
                lines.append(line)
        else:
            wrapped_text = textwrap.wrap(str(row[0]), col_name) or [""]
            for part in wrapped_text:
                line = f"| {fmt(part, col_name, 'left')} |"
                lines.append(line)

    lines.append("+" + "-" * (width - 2) + "+")
    return "\n".join(lines)


def get_package_xut():
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        print("No active user tokens found.")
        pause()
        return None

    packages = []
    data = get_family(api_key, tokens, PACKAGE_FAMILY_CODE)

    if not data:
        print("Failed to load package family data.")
        pause()
        return None

    clear_screen()
    table_width = shutil.get_terminal_size((100, 20)).columns

    family_name = data['package_family']["name"]
    print(render_table(f"FAMILY NAME: {family_name}", [], show_headers=False, width=table_width))

    start_number = 1
    for variant_number, variant in enumerate(data["package_variants"], start=1):
        variant_name = variant["name"]
        print(render_table(f"Variant {variant_number}: {variant_name}", [], show_headers=False, width=table_width))

        variant_table = []
        for option in variant["package_options"]:
            friendly_name = option["name"]
            if friendly_name.lower() == "vidio":
                friendly_name = "Unli Turbo Vidio"
            if friendly_name.lower() == "iflix":
                friendly_name = "Unli Turbo Iflix"

            variant_table.append([start_number, friendly_name, f"Rp {option['price']}"])

            packages.append({
                "number": start_number,
                "name": friendly_name,
                "price": option["price"],
                "code": option["package_option_code"]
            })
            start_number += 1

        if variant_table:
            print(render_table("PAKET", variant_table,
                               headers=["No", "Nama Paket", "Harga"], width=table_width))

    return packages
