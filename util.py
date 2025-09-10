import os, json
import sys
import re
import textwrap
from html.parser import HTMLParser

import requests  # masih dipakai kalau ada request di api_request.py

from api_request import *
from ui import *


def load_token(api_key: str):
    if os.path.exists("tokens.json"):
        with open("tokens.json", "r", encoding="utf8") as f:
            tokens = json.load(f)
        print("Tokens loaded successfully.")
        
        refresh_token = tokens.get("refresh_token")
        tokens = get_new_token(refresh_token) or {}
        
        id_token = tokens.get("id_token")
        access_token = tokens.get("access_token")
        
        profile = get_profile(api_key, access_token, id_token) or {}
        profile_data = profile.get("profile", {})
        phone_number = profile_data.get("msisdn")
        
        balance = get_balance(api_key, id_token) or {}
        balance_remaining = balance.get("remaining")
        balance_expired_at = balance.get("expired_at")
        
        return {
            "tokens": tokens,
            "is_logged_in": True,
            "phone_number": phone_number,
            "balance": balance_remaining,
            "balance_expired_at": balance_expired_at,
        }
    
    return None


# Load API key from text file named api.key
def load_api_key() -> str:
    if os.path.exists("api.key"):
        with open("api.key", "r", encoding="utf8") as f:
            api_key = f.read().strip()
        if api_key:
         #   print("API key loaded successfully.")
            return api_key
        else:
            print("API key file is empty.")
            return ""
    else:
        print("API key file not found.")
        return ""
    

def save_api_key(api_key: str):
    with open("api.key", "w", encoding="utf8") as f:
        f.write(api_key)
    print("API key saved successfully.")
    

def delete_api_key():
    if os.path.exists("api.key"):
        os.remove("api.key")
        print("API key file deleted.")
    else:
        print("API key file does not exist.")


def ensure_api_key() -> str:
    """
    Load api.key if present; otherwise prompt the user.
    Tidak lagi memverifikasi API key ke server.
    """
    # Try to load an existing key
    current = load_api_key()
    if current:
        return current

    # Prompt user if missing
    api_key = input("Masukkan API key: ").strip()
    if not api_key:
        print("API key tidak boleh kosong. Menutup aplikasi.")
        sys.exit(1)

    save_api_key(api_key)
    return api_key


class HTMLToText(HTMLParser):
    def __init__(self, width=100):
        super().__init__()
        self.width = width
        self.result = []
        self.in_li = False

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self.in_li = True
        elif tag == "br":
            self.result.append("\n")

    def handle_endtag(self, tag):
        if tag == "li":
            self.in_li = False
            self.result.append("\n")

    def handle_data(self, data):
        text = data.strip()
        if text:
            if self.in_li:
                self.result.append(f"- {text}")
            else:
                self.result.append(text)

    def get_text(self):
        # Join and clean multiple newlines
        text = "".join(self.result)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        # Wrap lines nicely
        return "\n".join(textwrap.wrap(text, width=self.width, replace_whitespace=False))


def display_html(html_text, width=100):
    parser = HTMLToText(width=width)
    parser.feed(html_text)
    return parser.get_text()
