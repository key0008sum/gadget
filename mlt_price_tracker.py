import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import time

# --- 設定エリア ---
# 1. 監視したい商品のリスト（名前、URL、目標価格を設定）
ITEMS_TO_TRACK = [
    {
        "name": "Apple AirPods 4",
        "url": "https://kakaku.com/item/K0001651424/",
        "target_price": 25000
    },
    {
        "name": "Apple iPad(第10世代)",
        "url": "https://kakaku.com/item/K0001476686/",
        "target_price": 50000
    }
]

# 2. DiscordのウェブフックURL
# DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1509168785918132284/5gN4-01hbAKyKDwkVzmirPjzcrFBUuNCDOuIgV8acfgoTV6l_LWMRsCaPmY4AMk12WAt"
# 変更後
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# 3. 前回の価格を記憶しておくためのファイル名
HISTORY_FILE = "price_history.json"
# -----------------

def load_history():
    """過去の価格データをファイルから読み込む"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_history(history_data):
    """現在の価格データをファイルに保存する"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=4)

def send_discord_notification(name, current_price, target_price, url):
    """Discordへ通知を送信する"""
    message = (
        f"🎉 **セール検知アラート**\n"
        f"「{name}」が目標価格を下回りました！\n"
        f"現在の価格: **{current_price}円** (目標: {target_price}円)\n"
        f"商品リンク: {url}"
    )
    payload = {"content": message}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
        print(f"  -> 📲 Discordへ通知を送信しました！")
    except Exception as e:
        print(f"  -> ❌ 通知送信エラー: {e}")

def main():
    print(f"=== 巡回開始: {datetime.datetime.now()} ===")
    
    # 前回の履歴を読み込む
    history = load_history()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # リストに入っている商品を1つずつ順番にチェックする
    for item in ITEMS_TO_TRACK:
        name = item["name"]
        url = item["url"]
        target = item["target_price"]
        
        print(f"\n🔍 チェック中: {name}")
        
        try:
            # サーバーに負担をかけないよう、1秒待機（スクレイピングのマナーです）
            time.sleep(1)
            
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f"  -> ⚠️ アクセス失敗 (Status: {response.status_code})")
                continue
                
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'html.parser')
            
            target_element = soup.select_one('.p-prdInfoLowprice_ttl')
            if not target_element:
                print("  -> ⚠️ 価格データの要素が見つかりません。")
                continue
                
            current_price = int(target_element.get('data-jsread-lowprice'))
            print(f"  -> 現在の最安値: {current_price}円 (目標: {target}円)")
            
            # --- 判定ロジック（記憶力付き） ---
            # 履歴にデータがない場合、または前回の価格と違う場合のみ比較を行う
            previous_price = history.get(name, float('inf'))
            
            if current_price <= target:
                if current_price < previous_price:
                    print(f"  -> 🎉 目標達成＆前回より値下がりしています！")
                    send_discord_notification(name, current_price, target, url)
                elif current_price == previous_price:
                    print(f"  -> 💤 すでに通知済みの価格帯です。今回は通知をスキップします。")
                else:
                    print(f"  -> 📈 値上がりしました。通知をスキップします。")
            else:
                print(f"  -> 💤 まだ目標価格に達していません。")
                
            # 今回の価格を履歴として更新する
            history[name] = current_price

        except Exception as e:
            print(f"  -> ❌ エラーが発生しました: {e}")

    # チェックが終わったら、すべての履歴をファイルに保存
    save_history(history)
    print("\n=== 巡回完了 ===")

if __name__ == "__main__":
    main()