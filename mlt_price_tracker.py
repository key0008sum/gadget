import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import time

# --- 設定エリア ---
ITEMS_FILE = "items.json"
HISTORY_FILE = "price_history.json"
# ポイント: DiscordのURLを管理する外部ファイルのパスを指定
WEBHOOKS_FILE = "discord_webhooks.json"

# 毎回の実行時に現在の価格一覧を通知する機能のON/OFFスイッチ
ENABLE_PERIODIC_REPORT = True
# -----------------

def load_items():
    if os.path.exists(ITEMS_FILE):
        with open(ITEMS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    print(f"⚠️ {ITEMS_FILE} が見つかりません。")
    return []

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_history(history_data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=4)

# ポイント: discord_webhooks.json からURLのリストを安全に読み込む関数
def load_webhooks():
    if os.path.exists(WEBHOOKS_FILE):
        with open(WEBHOOKS_FILE, "r", encoding="utf-8") as f:
            # 読み込んだURLから余計な記号をクレンジングしてリスト化
            raw_urls = json.load(f)
            return [url.strip("[]'\" ") for url in raw_urls if url.strip("[]'\" ")]
    print(f"⚠️ {WEBHOOKS_FILE} が見つかりません。")
    return []

def send_alert_notification(webhooks, name, current_price, target_price, url):
    """セール検知時の個別アラート通知"""
    message = (
        f"🎉 **セール検知アラート**\n"
        f"「{name}」が目標価格を下回りました！\n"
        f"現在の価格: **{current_price}円** (目標: {target_price}円)\n"
        f"商品リンク: {url}"
    )
    payload = {"content": message}
    
    # ポイント: 読み込んだ複数のURLに対してループで1つずつ確実に送信する
    for webhook_url in webhooks:
        try:
            requests.post(webhook_url, json=payload)
            print(f"  -> 📲 アラートをDiscordへ送信しました！")
        except Exception as e:
            print(f"  -> ❌ アラート送信エラー: {e}")

def main():
    print(f"=== 巡回開始: {datetime.datetime.now()} ===")
    
    # ポイント: 外部ファイルからDiscordのURLリストを取得
    webhooks = load_webhooks()
    if not webhooks:
        print("⚠️ 送信先のDiscord URLが設定されていないため終了します。")
        return

    items_to_track = load_items()
    if not items_to_track:
        print("終了します。")
        return

    history = load_history()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    report_lines = []

    for item in items_to_track:
        name = item["name"]
        url = item["url"]
        target = item["target_price"]
        
        print(f"\n🔍 チェック中: {name}")
        
        try:
            # ポイント: ConnectionResetError対策として待機時間を2秒に延長
            time.sleep(2)
            
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f"  -> ⚠️ アクセス失敗 (Status: {response.status_code})")
                report_lines.append(f"・{name}: 取得エラー ⚠️")
                continue
                
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'html.parser')
            
            target_element = soup.select_one('.p-prdInfoLowprice_ttl')
            if not target_element:
                print("  -> ⚠️ 価格データの要素が見つかりません。")
                report_lines.append(f"・{name}: 要素エラー ⚠️")
                continue
                
            current_price = int(target_element.get('data-jsread-lowprice'))
            print(f"  -> 現在の最安値: {current_price}円 (目標: {target}円)")
            
            report_lines.append(f"・{name}: **{current_price}円** (目標: {target}円)")

            previous_price = history.get(name, float('inf'))
            
            if current_price <= target:
                if current_price < previous_price:
                    print(f"  -> 🎉 目標達成＆前回より値下がりしています！")
                    send_alert_notification(webhooks, name, current_price, target, url)
                elif current_price == previous_price:
                    print(f"  -> 💤 すでに通知済みの価格帯です。スキップします。")
                else:
                    print(f"  -> 📈 値上がりしました。スキップします。")
            else:
                print(f"  -> 💤 まだ目標価格に達していません。")
                
            history[name] = current_price

        # ポイント: 接続強制切断などの例外エラーが発生してもシステムを止めず、ログに記録して次の商品に進む
        except Exception as e:
            print(f"  -> ❌ エラーが発生しました: {e}")
            report_lines.append(f"・{name}: エラー発生 ❌")

    save_history(history)
    
    # 定期報告の送信
    if ENABLE_PERIODIC_REPORT and report_lines:
        report_message = "📊 **【定期報告】現在の価格状況**\n" + "\n".join(report_lines)
        payload = {"content": report_message}
        
        # ポイント: 定期報告もすべてのURLへ順番に送信する
        for webhook_url in webhooks:
            try:
                requests.post(webhook_url, json=payload)
                print(f"📲 定期報告をDiscordへ送信しました！")
            except Exception as e:
                print(f"❌ 定期報告送信エラー: {e}")

    print("\n=== 巡回完了 ===")

if __name__ == "__main__":
    main()