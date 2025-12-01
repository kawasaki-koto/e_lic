import os
import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# ==========================================
# ★設定エリア
# ==========================================
LOGIN_URL = "https://www.e-license.jp/el31/lOZqZKHC3uM-brGQYS-1OA%3D%3D"
USER_ID = os.environ.get("USER_ID")
PASSWORD = os.environ.get("PASSWORD")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
DATA_FILE = "reservation_cache.json"
# ==========================================

def send_discord_notify(message):
    """Discordへの通知送信（ログ付き）"""
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ Webhook URLが未設定のため、通知をスキップします。")
        return
    
    print(f"🔔 Discord送信開始: {message[:30]}...") # 長いので先頭だけ表示
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
        if response.status_code in [200, 204]:
            print("✅ Discord送信成功")
        else:
            print(f"❌ Discord送信失敗: ステータスコード {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Discord送信エラー: {e}")

def load_previous_slots():
    """前回のデータを読み込む"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"📂 保存されたデータ({DATA_FILE})を読み込みました: {len(data)}件")
                return set(data)
        except Exception as e:
            print(f"⚠️ データ読み込みエラー（初回実行の可能性あり）: {e}")
            return set()
    print("ℹ️ 保存ファイルがないため、初回実行として扱います。")
    return set()

def save_current_slots(slots_set):
    """今回のデータを保存する"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(list(slots_set), f, ensure_ascii=False, indent=2)
        print(f"💾 データをファイル({DATA_FILE})に保存しました。")
    except Exception as e:
        print(f"❌ データ保存エラー: {e}")

def get_available_slots():
    print("🚀 ブラウザを起動します...")
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument("--window-size=1280,1024")

    # ドライバ起動
    try:
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=options
        )
    except Exception as e:
        print(f"❌ ブラウザ起動エラー: {e}")
        return set()

    found_slots_set = set()

    try:
        print(f"🌐 ログインページへアクセス: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        time.sleep(3)

        print("🔑 ログイン情報を入力中...")
        driver.find_element(By.NAME, "studentId").send_keys(USER_ID)
        driver.find_element(By.NAME, "password").send_keys(PASSWORD)
        
        print("👆 ログインボタンをクリック...")
        try:
            driver.find_element(By.ID, "login").click()
        except:
            print("   (ID='login'が見つからないため、XPATHでボタンを探します)")
            driver.find_element(By.XPATH, "//input[@value='ログイン']").click()
            
        print("⏳ ページ遷移を待機中(5秒)...")
        time.sleep(5)

        # 空き状況取得
        # ============================================================
        # 【修正箇所】 mikata-table を除外するためのCSSセレクタに変更
        # .status1:not(.mikata-table) 
        # → status1クラスを持つが、mikata-tableクラスは持たない要素
        # ============================================================
        print("🔎 空き枠要素(class='status1', 除外='mikata-table')を検索中...")
        
        open_slots_elements = driver.find_elements(By.CSS_SELECTOR, ".status1:not(.mikata-table)")
        
        print(f"   ➡ 発見した要素数(誤検知除外済み): {len(open_slots_elements)}")
        send_discord_notify(f"🔎 検索完了。発見数: {len(open_slots_elements)}")
        
        if len(open_slots_elements) > 0:
            for i, element in enumerate(open_slots_elements):
                try:
                    if not element.is_displayed():
                        # 非表示の要素はログに出しつつスキップ
                        print(f"   [スキップ] 要素{i}は非表示です")
                        continue
                    
                    link = element.find_element(By.TAG_NAME, "a")
                    
                    # 属性を取得
                    d_date = link.get_attribute('data-date')
                    d_week = link.get_attribute('data-week')
                    d_time = link.get_attribute('data-time')
                    
                    # データが欠けている場合はスキップ
                    if not d_date or not d_time:
                         continue

                    info = f"{d_date}{d_week} {d_time}"
                    
                    print(f"   🎉 空き枠データを抽出: {info}")
                    found_slots_set.add(info)

                except Exception as e:
                    # mikata-table以外にもaタグを持たないstatus1がある場合の対策
                    # print(f"   ⚠️ 要素{i}の解析中にエラー: {e}")
                    pass

    except Exception as e:
        print(f"⚠️ エラー: {e}")
        pass
    finally:
        print("👋 ブラウザを閉じます")
        driver.quit()
    
    return found_slots_set

if __name__ == "__main__":
    print("========================================")
    print("🤖 予約監視ボット 実行開始")
    print("========================================")
    
    # 0. 環境変数のチェック
    if not USER_ID or not PASSWORD:
        print("❌ エラー: USER_ID または PASSWORD が設定されていません。Secretsを確認してください。")
        exit(1)

    # 1. 前回のデータを読み込み
    previous_slots = load_previous_slots()
    
    # 2. 今回のデータを取得
    current_slots = get_available_slots()
    print(f"📊 集計結果: 今回の空き枠数 = {len(current_slots)}")
    
    # 3. 差分を計算 (今回 - 前回)
    new_added_slots = current_slots - previous_slots
    print(f"🆕 新規追加分の計算: {len(new_added_slots)}件")

    # 4. 通知判定
    if len(new_added_slots) > 0:
        print("🚀 新規空き枠があります！Discordへ通知します。")
        msg = f"@here 🎉 **{len(new_added_slots)}件** の新規空き枠が出ました！\n\n"
        for slot in new_added_slots:
            msg += f"🚗 **{slot}**\n"
            print(f"   - {slot}") # ログにも出す
        
        msg += f"\n[予約サイトへ]({LOGIN_URL})"
        
        send_discord_notify(msg)
    else:
        print("💤 新規の空き枠はありませんでした。")

    # 5. 今回の結果を保存
    save_current_slots(current_slots)
    
    print("========================================")
    print("✅ 全処理完了")
    print("========================================")