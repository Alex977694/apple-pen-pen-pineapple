import os
import re
import time
import requests
from threading import Thread
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# Скан хийсэн үр дүнг санах ойд хадгалах глобал хувьсагч
SCANNED_WALLETS = []
ACTIVE_WALLETS = []

def parse_result_file():
    """/data/result.txt эсвэл result.txt файлоос хаяг болон түлхүүрүүдийг унших"""
    wallets = []
    result_file = "/data/result.txt" if os.path.exists("/data/result.txt") else "result.txt"
    
    if not os.path.exists(result_file):
        return wallets
        
    with open(result_file, "r", encoding="utf-8") as f:
        content = f.read()
        
    blocks = content.split("========================================")
    for block in blocks:
        if "Key:" not in block:
            continue
        key_match = re.search(r"Key:\s*([a-fA-F0-9]{64})", block)
        key = key_match.group(1) if key_match else ""
        
        lines = block.strip().split("\n")
        details = []
        for line in lines:
            if "💰" in line:
                details.append(line.strip())
        
        if key:
            wallets.append({"key": key, "details": details, "is_active": False})
    return wallets

def check_address_activity(address):
    """Etherscan болон бусад нээлттэй API-уудаар гүйлгээ болон баланс шалгах хөнгөн логик"""
    # Жишээ нь Blockscan / Public RPC эсвэл файл доторх анхны мэдээллээс шалгана
    # Энд файл доторх гүйлгээний тоо болон балансыг задлан шинжилж идэвхтэй эсэхийг тогтооно
    pass

def background_scanner():
    """10-15 минут (900 секунд) тутамд автоматаар шалгадаг фонны процесс"""
    global SCANNED_WALLETS, ACTIVE_WALLETS
    while True:
        try:
            print("[BACKGROUND SCANNER] Starting chain scan for updated wallets...")
            raw_wallets = parse_result_file()
            active_list = []
            
            for w in raw_wallets:
                has_balance_or_tx = False
                for detail in w['details']:
                    # Баланстай (0.0-ээс их) эсэхийг шалгах
                    if "Баланс:" in detail and "Баланс: 0.0" not in detail and "0.0 BTC" not in detail:
                        has_balance_or_tx = True
                    # Гүйлгээтэй (0-ээс их) эсэхийг шалгах
                    tx_match = re.search(r"Гүйлгээ:\s*(\d+)", detail)
                    if tx_match and int(tx_match.group(1)) > 0:
                        has_balance_or_tx = True
                
                w['is_active'] = has_balance_or_tx
                if has_balance_or_tx:
                    active_list.append(w)
            
            # Баланстай/Гүйлгээтэйг нь дээш нь эрэмбэлэх
            raw_wallets.sort(key=lambda x: x['is_active'], reverse=True)
            
            SCANNED_WALLETS = raw_wallets
            ACTIVE_WALLETS = active_list
            print(f"[BACKGROUND SCANNER] Done. Total: {len(SCANNED_WALLETS)}, Active: {len(ACTIVE_WALLETS)}")
        except Exception as e:
            print(f"[BACKGROUND SCANNER ERROR] {e}")
            
        # 10 минут (600 секунд) тутамд дахин шалгана
        time.sleep(600)

# Flask асахтай хамт Background Thread-ийг эхлүүлэх
scanner_thread = Thread(target=background_scanner, daemon=True)
scanner_thread.start()

# HTML Загвар
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="60"> <!-- 1 минут тутамд автоматаар шинэчлэгдэнэ -->
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: Consolas, monospace; padding: 20px; }
        h1 { color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 10px; }
        .card { background: #161b22; border: 1px solid #30363d; padding: 15px; margin-bottom: 15px; border-radius: 6px; }
        .active-card { border: 2px solid #238636; background: #0e2a1f; }
        .key { color: #f2e05a; font-weight: bold; }
        .detail { margin-left: 20px; color: #79c0ff; }
        .badge { background: #238636; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; margin-bottom: 8px; display: inline-block; }
        .nav { margin-bottom: 20px; }
        .nav a { color: #58a6ff; text-decoration: none; margin-right: 15px; font-weight: bold; }
        .nav a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/tx/result">📋 Бүх Түрүүвч (/tx/result)</a>
        <a href="/tx/changed" style="color: #3fb950;">🔥 Зөвхөн Өөрчлөгдсөн/Идэвхтэй Түрүүвч (/tx/changed)</a>
    </div>

    <h1>{{ title }}</h1>
    <p>Нийт жагсаалтад байгаа: <strong>{{ wallets|length }}</strong></p>

    {% for w in wallets %}
    <div class="card {% if w.is_active %}active-card{% endif %}">
        {% if w.is_active %}
        <div class="badge">🔥 ONTSGOILSON / ACTIVE / CHANGED</div>
        {% endif %}
        <div>🔑 <span class="key">Key:</span> {{ w.key }}</div>
        {% for d in w.details %}
        <div class="detail">{{ d }}</div>
        {% endfor %}
    </div>
    {% else %}
    <p style="color: #8b949e;">Одоогоор ямар нэгэн өөрчлөлтэй/идэвхтэй түрүүвч олдсон огүй байна...</p>
    {% endfor %}
</body>
</html>
"""

@app.route("/tx/result")
def show_results():
    wallets = SCANNED_WALLETS if SCANNED_WALLETS else parse_result_file()
    return render_template_string(HTML_TEMPLATE, title="🚀 Monitored Crypto Wallets Dashboard (All)", wallets=wallets)

@app.route("/tx/changed")
def show_changed():
    wallets = ACTIVE_WALLETS if SCANNED_WALLETS else [w for w in parse_result_file() if w.get('is_active')]
    return render_template_string(HTML_TEMPLATE, title="🔥 Changed & Active Crypto Wallets Only", wallets=wallets)

@app.route("/")
def home():
    return "Crypto Monitor Server is Running! Go to <a href='/tx/result'>/tx/result</a> or <a href='/tx/changed'>/tx/changed</a>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
