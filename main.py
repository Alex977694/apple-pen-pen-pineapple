import os
import re
import time
from threading import Thread
from flask import Flask, render_template_string

app = Flask(__name__)

# Сканнер болон өөрчлөлтийг хянах глобал санах ой
PREVIOUS_WALLETS_STATE = {} # {key: {chain: tx_count, balance: val}}
CHANGED_WALLETS = []
ALL_WALLETS = []

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
                
                # 1. Жинхэнэ долларын үлдэгдэл > $0.00 байгаа эсэхийг шалгах ($0.01 ба түүнээс дээш)
                usd_match = re.search(r"\$\s*([\d\.]+)\s*USD", line_str)
                if usd_match:
                    try:
                        usd_val = float(usd_match.group(1))
                        if usd_val > 0.00:
                            has_valuable_balance = True
                    except ValueError:
                        pass

                # 2. Гүйлгээний тоо болон сүлжээг бүртгэж авах (Өөрчлөлт харьцуулахад зориулж)
                chain_match = re.search(r"💰\s*([^\n\[]+)", line_str)
                tx_match = re.search(r"Гүйлгээ:\s*(\d+)", line_str)
                if chain_match and tx_match:
                    chain_name = chain_match.group(1).strip()
                    tx_count = int(tx_match.group(1))
                    chain_tx_data[chain_name] = tx_count

        if key:
            wallets.append({
                "key": key,
                "details": details,
                "has_balance": has_valuable_balance,
                "tx_data": chain_tx_data
            })
    return wallets

def background_scanner():
    global PREVIOUS_WALLETS_STATE, CHANGED_WALLETS, ALL_WALLETS
    while True:
        try:
            current_wallets = parse_result_file()
            ALL_WALLETS = current_wallets
            
            new_changed = []
            
            # Эхний удаа уншиж байгаа бол санах ойдоо бүртгээд авна
            if not PREVIOUS_WALLETS_STATE:
                for w in current_wallets:
                    PREVIOUS_WALLETS_STATE[w['key']] = w['tx_data']
            else:
                # Дараагийн удаа уншихад TX тоо өөрчлөгдсөн үү гэдгийг тулгана
                for w in current_wallets:
                    k = w['key']
                    current_txs = w['tx_data']
                    prev_txs = PREVIOUS_WALLETS_STATE.get(k, {})
                    
                    # Гүйлгээний тоо шинэчлэгдсэн эсэхийг шалгах
                    is_tx_changed = False
                    for chain, tx_cnt in current_txs.items():
                        if chain not in prev_txs or prev_txs[chain] != tx_cnt:
                            is_tx_changed = True
                            break
                    
                    if is_tx_changed or w['has_balance']:
                        new_changed.append(w)
                    
                    # Шинэ төлөвийг хадгалах
                    PREVIOUS_WALLETS_STATE[k] = current_txs
                    
                CHANGED_WALLETS = new_changed

            print(f"[SCANNER] Total: {len(ALL_WALLETS)}, Changed/Has Balance: {len(CHANGED_WALLETS)}")
        except Exception as e:
            print(f"[SCANNER ERROR] {e}")
            
        time.sleep(300) # 5 минут тутамд шалгана

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
        .balance-card { border: 2px solid #238636; background: #0e2a1f; }
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
        <a href="/tx/changed" style="color: #3fb950;">🔥 Зөвхөн Өөрчлөгдсөн/Баланстай Түрүүвч (/tx/changed)</a>
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
    <p style="color: #8b949e;">Одоогоор ямар нэгэн шинэ гүйлгээний өөрчлөлт эсвэл баланстай түрүүвч олдсонгүй...</p>
    {% endfor %}
</body>
</html>
"""

@app.route("/tx/result")
def show_results():
    wallets = ALL_WALLETS if ALL_WALLETS else parse_result_file()
    return render_template_string(HTML_TEMPLATE, title="🚀 Monitored Crypto Wallets Dashboard (All)", wallets=wallets)

@app.route("/tx/changed")
def show_changed():
    return render_template_string(HTML_TEMPLATE, title="🔥 Changed Transactions & Balance Wallets Only", wallets=CHANGED_WALLETS)

@app.route("/")
def home():
    return "Crypto Monitor Server is Running! Go to <a href='/tx/result'>/tx/result</a> or <a href='/tx/changed'>/tx/changed</a>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
