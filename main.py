import os
import re
import time
from threading import Thread
from flask import Flask, render_template_string

app = Flask(__name__)

SCANNED_WALLETS = []
ACTIVE_WALLETS = []

def parse_result_file():
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
        has_real_balance = False
        
        for line in lines:
            if "💰" in line:
                details.append(line.strip())
                # Зөвхөн баланс нь 0.0-ээс их буюу криптовалюттай үед л идэвхтэй гэж үзэх
                if "Баланс:" in line:
                    if not ("Баланс: 0.0" in line or "0.0 BTC" in line or "9e-15" in line or "2.8e-17" in line):
                        has_real_balance = True
                    # Хэрэв баланс дээр тодорхой дүнтэй байвал
                    if "USD" in line and not ("$0.00 USD" in line):
                        has_real_balance = True
        
        if key:
            wallets.append({
                "key": key, 
                "details": details, 
                "is_active": has_real_balance
            })
    return wallets

def background_scanner():
    global SCANNED_WALLETS, ACTIVE_WALLETS
    while True:
        try:
            raw_wallets = parse_result_file()
            active_list = [w for w in raw_wallets if w['is_active']]
            
            SCANNED_WALLETS = raw_wallets
            ACTIVE_WALLETS = active_list
            print(f"[SCANNER] Total: {len(SCANNED_WALLETS)}, Active with balance: {len(ACTIVE_WALLETS)}")
        except Exception as e:
            print(f"[ERROR] {e}")
        time.sleep(300) # 5 минут тутамд

scanner_thread = Thread(target=background_scanner, daemon=True)
scanner_thread.start()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="60">
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
        <a href="/tx/changed" style="color: #3fb950;">🔥 Зөвхөн Баланстай/Идэвхтэй Түрүүвч (/tx/changed)</a>
    </div>

    <h1>{{ title }}</h1>
    <p>Нийт жагсаалтад байгаа: <strong>{{ wallets|length }}</strong></p>

    {% for w in wallets %}
    <div class="card {% if w.is_active %}active-card{% endif %}">
        {% if w.is_active %}
        <div class="badge">🔥 REAL BALANCE / ACTIVE</div>
        {% endif %}
        <div>🔑 <span class="key">Key:</span> {{ w.key }}</div>
        {% for d in w.details %}
        <div class="detail">{{ d }}</div>
        {% endfor %}
    </div>
    {% else %}
    <p style="color: #8b949e;">Одоогоор ямар нэгэн баланстай идэвхтэй түрүүвч олдсонгүй...</p>
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
    wallets = ACTIVE_WALLETS if SCANNED_WALLETS else [w for w in parse_result_file() if w['is_active']]
    return render_template_string(HTML_TEMPLATE, title="🔥 Active Wallets with Balance Only", wallets=wallets)

@app.route("/")
def home():
    return "Crypto Monitor Server is Running! Go to <a href='/tx/result'>/tx/result</a> or <a href='/tx/changed'>/tx/changed</a>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
