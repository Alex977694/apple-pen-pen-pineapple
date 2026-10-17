import os
import re
import time
from threading import Thread
from flask import Flask, render_template_string, Response

# Өөрийн үүсгэсэн модулийг импортлох
import github64

app = Flask(__name__)

SCANNED_WALLETS = []
CHANGED_WALLETS = []
PREVIOUS_WALLETS_STATE = {}

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
        has_valuable_balance = False
        chain_tx_data = {}
        for line in lines:
            if "💰" in line:
                line_str = line.strip()
                details.append(line_str)
                usd_match = re.search(r"\$\s*([\d\.]+)\s*USD", line_str)
                if usd_match:
                    try:
                        if float(usd_match.group(1)) > 0.00:
                            has_valuable_balance = True
                    except ValueError:
                        pass
                chain_match = re.search(r"💰\s*([^\n\[]+)", line_str)
                tx_match = re.search(r"Гүйлгээ:\s*(\d+)", line_str)
                if chain_match and tx_match:
                    chain_tx_data[chain_match.group(1).strip()] = int(tx_match.group(1))
        if key:
            wallets.append({"key": key, "details": details, "has_balance": has_valuable_balance, "tx_data": chain_tx_data})
    return wallets

def background_wallet_scanner():
    global PREVIOUS_WALLETS_STATE, CHANGED_WALLETS, SCANNED_WALLETS
    while True:
        try:
            current_wallets = parse_result_file()
            SCANNED_WALLETS = current_wallets
            new_changed = []
            if not PREVIOUS_WALLETS_STATE:
                for w in current_wallets:
                    PREVIOUS_WALLETS_STATE[w['key']] = w['tx_data']
            else:
                for w in current_wallets:
                    k = w['key']
                    current_txs = w['tx_data']
                    prev_txs = PREVIOUS_WALLETS_STATE.get(k, {})
                    is_tx_changed = any(chain in prev_txs and prev_txs[chain] != tx_cnt for chain, tx_cnt in current_txs.items())
                    if is_tx_changed:
                        new_changed.append(w)
                    PREVIOUS_WALLETS_STATE[k] = current_txs
                CHANGED_WALLETS = new_changed
        except Exception as e:
            print(f"[WALLET SCANNER ERROR] {e}")
        time.sleep(300)

Thread(target=background_wallet_scanner, daemon=True).start()

# --- GITHUB SCANNER ROUTES ---
@app.route('/git64/start')
def start_git64():
    success, msg = github64.start_scanner()
    return msg  # Зөвхөн стринг мессежийг буцаана

@app.route("/git64/stop")
def stop_git64():
    success, msg = github64.stop_scanner()
    return msg  # Зөвхөн стринг мессежийг буцаана

@app.route("/git64/text")
def view_git64_text():
    return Response(github64.get_tokens_text(), mimetype="text/plain")

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
        .balance-card { border: 2px solid #238636; background: #0e2a1f; }
        .key { color: #f2e05a; font-weight: bold; }
        .detail { margin-left: 20px; color: #79c0ff; }
        .badge { background: #238636; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; margin-bottom: 8px; display: inline-block; }
        .nav { margin-bottom: 20px; }
        .nav a { color: #58a6ff; text-decoration: none; margin-right: 15px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/tx/result">📋 Бүх Түрүүвч</a>
        <a href="/tx/changed" style="color: #3fb950;">🔥 Өөрчлөгдсөн Түрүүвч</a>
        <a href="/git64/start" style="color: #e3b341;">▶️ Git Start</a>
        <a href="/git64/stop" style="color: #f85149;">⏹️ Git Stop</a>
        <a href="/git64/text" style="color: #a5d6ff;">📄 Git TXT</a>
    </div>

    <h1>{{ title }}</h1>
    <p>Жагсаалтад байгаа: <strong>{{ wallets|length }}</strong></p>

    {% for w in wallets %}
    <div class="card {% if w.has_balance %}balance-card{% endif %}">
        {% if w.has_balance %}
        <div class="badge">💰 BALANCE > $0.00 FOUND</div>
        {% endif %}
        <div>🔑 <span class="key">Key:</span> {{ w.key }}</div>
        {% for d in w.details %}
        <div class="detail">{{ d }}</div>
        {% endfor %}
    </div>
    {% else %}
    <p style="color: #8b949e;">Одоогоор мэдээлэл олдсонгүй...</p>
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
    return render_template_string(HTML_TEMPLATE, title="🔥 Changed Transactions Only", wallets=CHANGED_WALLETS)

@app.route("/")
def home():
    return "Server is Running! Dashboard: <a href='/tx/result'>/tx/result</a> | Git Scanner: <a href='/git64/start'>/git64/start</a>"

@app.route('/git64/clear')
def git64_clear():
    result = github64.clear_tokens()
    return result

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
