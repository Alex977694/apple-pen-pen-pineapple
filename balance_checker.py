import os
import requests
import hashlib
import base58
import ecdsa
from concurrent.futures import ThreadPoolExecutor, as_completed
from eth_account import Account

# EVM сүлжээнүүд
EVM_CHAINS = {
    "Ethereum (ETH)": "https://ethereum-rpc.publicnode.com",
    "BNB Smart Chain (BNB)": "https://bsc-rpc.publicnode.com",
    "Polygon (POL)": "https://polygon-bor-rpc.publicnode.com",
    "Arbitrum (ETH)": "https://arbitrum-one-rpc.publicnode.com",
    "Optimism (ETH)": "https://optimism-rpc.publicnode.com",
    "Base (ETH)": "https://base-rpc.publicnode.com",
    "Avalanche (AVAX)": "https://avalanche-c-chain-rpc.publicnode.com",
    "Gnosis (xDAI)": "https://gnosis-rpc.publicnode.com",
    "zkSync Era (ETH)": "https://mainnet.era.zksync.io",
    "Linea (ETH)": "https://rpc.linea.build",
    "Scroll (ETH)": "https://rpc.scroll.io",
    "Celo (CELO)": "https://forno.celo.org",
    "Moonbeam (GLMR)": "https://rpc.api.moonbeam.network",
}

# 🛠 Railway volume замуудыг github64.py-тэй яг ижил байхаар тохируулав
if os.path.exists("/data"):
    PRIVATES_PATH = "/data/privates.txt"
    RESULT_PATH = "/data/result.txt"
    BLACKLIST_PATH = "/data/blacklist.txt"
    print(f"📁 Balance Checker Railway /data Volume ашиглаж байна.")
else:
    PRIVATES_PATH = "privates.txt"
    RESULT_PATH = "result.txt"
    BLACKLIST_PATH = "blacklist.txt"
    print(f"⚠️ Balance Checker локал файл ашиглаж байна.")

def private_key_to_btc_address(priv_key_hex):
    try:
        priv_bytes = bytes.fromhex(priv_key_hex)
        sk = ecdsa.SigningKey.from_string(priv_bytes, curve=ecdsa.SECP256k1)
        vk = sk.get_verifying_key()
        pub_bytes = b'\x04' + vk.to_string()
        compressed_pub = b'\x02' + pub_bytes[1:33] if pub_bytes[-1] % 2 == 0 else b'\x03' + pub_bytes[1:33]
        sha = hashlib.sha256(compressed_pub).digest()
        ripemd = hashlib.new('ripemd160', sha).digest()
        ver_ripemd = b'\x00' + ripemd
        checksum = hashlib.sha256(hashlib.sha256(ver_ripemd).digest()).digest()[:4]
        return base58.b58encode(ver_ripemd + checksum).decode('utf-8')
    except:
        return None

def get_usd_value(coin_symbol, balance):
    """Балансыг тухайн коины яг бодит ханшаар USD руу хөрвүүлэх"""
    try:
        coin_map = {
            "ETH": "ethereum", 
            "BNB": "binancecoin", 
            "BTC": "bitcoin", 
            "POL": "polygon-ecosystem-token",
            "AVAX": "avalanche-2",
            "xDAI": "xdai",
            "CELO": "celo",
            "GLMR": "moonbeam"
        }
        id_name = coin_map.get(coin_symbol)
        if not id_name or balance <= 0:
            return 0.0
            
        res = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={id_name}&vs_currencies=usd", timeout=3)
        if res.status_code == 200:
            price = res.json().get(id_name, {}).get("usd", 0)
            return balance * price
    except:
        pass
    return 0.0

def check_single_key(clean_key):
    report_details = []
    total_activity = 0
    
    session = requests.Session()
    
    # 1. EVM Networks
    try:
        evm_key = "0x" + clean_key
        account = Account.from_key(evm_key)
        eth_address = account.address
        
        for name, rpc in EVM_CHAINS.items():
            try:
                res_bal = session.post(rpc, json={"jsonrpc": "2.0", "method": "eth_getBalance", "params": [eth_address, "latest"], "id": 1}, timeout=3)
                res_txs = session.post(rpc, json={"jsonrpc": "2.0", "method": "eth_getTransactionCount", "params": [eth_address, "latest"], "id": 2}, timeout=3)
                
                bal = int(res_bal.json().get("result", "0"), 16) / 10**18 if res_bal.status_code == 200 and "result" in res_bal.json() else 0
                tx_count = int(res_txs.json().get("result", "0"), 16) if res_txs.status_code == 200 and "result" in res_txs.json() else 0
                
                if bal > 0 or tx_count > 0:
                    symbol = "ETH"
                    if "BNB" in name: symbol = "BNB"
                    elif "Polygon" in name: symbol = "POL"
                    elif "Avalanche" in name: symbol = "AVAX"
                    elif "Gnosis" in name: symbol = "xDAI"
                    elif "Celo" in name: symbol = "CELO"
                    elif "Moonbeam" in name: symbol = "GLMR"
                    
                    usd_val = get_usd_value(symbol, bal)
                    usd_str = f" (~ ${usd_val:.2f} USD)" if usd_val > 0 else ""
                    
                    bal_str = f"{bal:.8f}".rstrip('0').rstrip('.') if bal > 0 else "0.0"
                    if bal_str == "": bal_str = "0.0"

                    report_details.append(f"   💰 {name} [{eth_address}] -> Баланс: {bal_str}{usd_str} | Гүйлгээ: {tx_count}")
                    total_activity += 1
            except:
                pass
    except:
        pass

    # 2. Bitcoin (BTC)
    btc_address = private_key_to_btc_address(clean_key)
    if btc_address:
        try:
            res = session.get(f"https://blockchain.info/balance?active={btc_address}", timeout=4)
            if res.status_code == 200:
                data = res.json().get(btc_address, {})
                btc_bal = data.get("final_balance", 0) / 10**8
                btc_txs = data.get("n_tx", 0)
                if btc_bal > 0 or btc_txs > 0:
                    usd_val = get_usd_value("BTC", btc_bal)
                    usd_str = f" (~ ${usd_val:.2f} USD)" if usd_val > 0 else ""
                    
                    btc_bal_str = f"{btc_bal:.8f}".rstrip('0').rstrip('.') if btc_bal > 0 else "0.0"
                    if btc_bal_str == "": btc_bal_str = "0.0"

                    report_details.append(f"   💰 Bitcoin (BTC) [{btc_address}] -> Баланс: {btc_bal_str} BTC{usd_str} | Гүйлгээ: {btc_txs}")
                    total_activity += 1
        except:
            pass

    return clean_key, total_activity, report_details

def run_balance_checker_loop():
    print("🚀 SERVER-SIDE BALANCE CHECKER WORKER STARTED!")
    import time
    
    while True:
        try:
            if not os.path.exists(PRIVATES_PATH):
                time.sleep(10)
                continue

            already_checked = set()
            for fpath in [RESULT_PATH, BLACKLIST_PATH]:
                if os.path.exists(fpath):
                    with open(fpath, "r", encoding="utf-8") as rf:
                        for line in rf:
                            line_str = line.strip().lower()
                            if len(line_str) == 64:
                                already_checked.add(line_str)
                            elif "key:" in line_str:
                                parts = line_str.split("key:")
                                if len(parts) > 1:
                                    already_checked.add(parts[1].strip())

            with open(PRIVATES_PATH, "r", encoding="utf-8") as f:
                all_keys = list(set([line.strip().lower() for line in f if len(line.strip()) == 64]))

            keys = [k for k in all_keys if k not in already_checked]

            if not keys:
                time.sleep(15)
                continue

            print(f"📁 Шалгах шинэ {len(keys)} түлхүүр олдлоо. Шалгаж байна...")

            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = {executor.submit(check_single_key, key): key for key in keys}
                
                for future in as_completed(futures):
                    try:
                        key, activity, details = future.result()
                        clean_k = key.lower()
                        
                        if activity > 0:
                            print(f"🎉 АМЖИЛТТАЙ! Түлхүүр: {clean_k}")
                            os.makedirs(os.path.dirname(RESULT_PATH) if os.path.dirname(RESULT_PATH) else ".", exist_ok=True)
                            with open(RESULT_PATH, "a", encoding="utf-8") as rf:
                                rf.write(f"========================================\n")
                                rf.write(f"Key: {clean_k}\n")
                                for d in details:
                                    rf.write(f"{d}\n")
                                rf.write(f"========================================\n\n")
                        else:
                            os.makedirs(os.path.dirname(BLACKLIST_PATH) if os.path.dirname(BLACKLIST_PATH) else ".", exist_ok=True)
                            with open(BLACKLIST_PATH, "a", encoding="utf-8") as bf:
                                bf.write(f"{clean_k}\n")
                    except Exception as e:
                        pass
        except Exception as e:
            print(f"Worker Loop алдаа: {e}")
            
        time.sleep(10)

def get_blacklist_text():
    if os.path.exists(BLACKLIST_PATH):
        with open(BLACKLIST_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "Blacklist файл хоосон байна."

def clear_blacklist():
    try:
        if os.path.exists(BLACKLIST_PATH):
            with open(BLACKLIST_PATH, "w", encoding="utf-8") as f:
                f.write("")
            return "🗑️ Blacklist амжилттай цэвэрлэгдлээ."
        return "💡 Blacklist файл олдсонгүй."
    except Exception as e:
        return f"❌ Алдаа: {e}"
