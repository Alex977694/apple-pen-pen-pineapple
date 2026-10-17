import os
import re
from flask import Flask, render_template_string

app = Flask(__name__)

def parse_result_file():
    """result.txt файлоос хаяг болон гүйлгээний тоог задлан унших"""
    wallets = []
    result_file = "result.txt"
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
            wallets.append({"key": key, "details": details})
    return wallets

# Flask Вэб хуудас (Dashboard)
@app.route("/tx/result")
def show_results():
    wallets = parse_result_file()
    
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Crypto Monitor Dashboard</title>
        <meta charset="utf-8">
        <style>
            body { background-color: #121212; color: #00ff00; font-family: Consolas, monospace; padding: 20px; }
            h1 { color: #fff; border-bottom: 2px solid #00ff00; padding-bottom: 10px; }
            .card { background: #1e1e1e; border: 1px solid #333; padding: 15px; margin-bottom: 15px; border-radius: 5px; }
            .key { color: #ff9900; font-weight: bold; }
            .detail { margin-left: 20px; color: #00ffff; }
        </style>
    </head>
    <body>
        <h1>🚀 Monitored Crypto Wallets Dashboard</h1>
        <p>Нийт хянагдаж буй түлхүүрүүд: {{ wallets|length }}</p>
        {% for w in wallets %}
        <div class="card">
            <div>🔑 <span class="key">Key:</span> {{ w.key }}</div>
            {% for d in w.details %}
            <div class="detail">{{ d }}</div>
            {% endfor %}
        </div>
        {% endfor %}
    </body>
    </html>
    """
    return render_template_string(html_template, wallets=wallets)

@app.route("/")
def home():
    return "Crypto Monitor Server is Running! Go to <a href='/tx/result'>/tx/result</a>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
