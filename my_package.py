from api_request import get_package, send_api_request
from ui import clear_screen, pause, show_package_details, render_table
from auth_helper import AuthInstance

TABLE_WIDTH = 100  # Lebar tabel

col1_width = 10
col2_width = TABLE_WIDTH - (col1_width + 3*2 + 1)  # 2 kolom + spasi + border
def fetch_my_packages():
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        print(render_table("ERROR", [["Pesan", "No active user tokens found"]]))
        pause()
        return None

    id_token = tokens.get("id_token")
    path = "api/v8/packages/quota-details"
    payload = {
        "is_enterprise": False,
        "lang": "en",
        "family_member_id": ""
    }

    print(render_table("INFO", [["Fetching my packages..."]]))
    res = send_api_request(api_key, path, payload, id_token, "POST")

    if res.get("status") != "SUCCESS":
        print(render_table("ERROR", [
            ["Failed to fetch packages"],
            ["Response", str(res)]
        ]))
        pause()
        return None

    quotas = res["data"]["quotas"]
    clear_screen()

    my_packages = []
    num = 1
    for quota in quotas:
        quota_code = quota["quota_code"]
        group_code = quota["group_code"]
        name = quota["name"]
        family_code = "N/A"

      #  print(render_table(
  #  f"FETCH PACKAGE {num}",
  #  [["Fetching package details..."]],
 #   headers=["Key"],   # optional, bisa dipakai atau tidak
   # show_headers=False,
  #  aligns=["Center"]
#))
        package_details = get_package(api_key, tokens, quota_code)
        if package_details:
            family_code = package_details.get("package_family", {}).get("package_family_code", "N/A")

        # Tampilkan paket sebagai tabel
        package_table = [
            ["Name", name],
            ["Quota Code", quota_code],
            ["Family Code", family_code],
            ["Group Code", group_code]
        ]
      #  print(render_table(f"PACKAGE {num}", package_table))
        print(render_table(
    f"PACKAGE DETAILS {num}",
    package_table,
    aligns=["left", "left"] # kiri semua
))
        my_packages.append({
            "number": num,
            "quota_code": quota_code,
        })
        num += 1

    # Pilihan rebuy
    print(render_table("INFO", [["Rebuy package? Input package number to rebuy, or '00' to back."]]))
    choice = input("Choice: ")
    if choice == "00":
        return None

    selected_pkg = next((pkg for pkg in my_packages if str(pkg["number"]) == choice), None)

    if not selected_pkg:
        print(render_table("ERROR", [["Paket tidak ditemukan. Silakan masukan nomor yang benar"]]))
        pause()
        return None

    is_done = show_package_details(api_key, tokens, selected_pkg["quota_code"])
    if is_done:
        return None

    pause()
