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
# ★設定エリア (環境変数から読み込むように変更)
# ==========================================
# 実際の値はGitHubの「Secrets」に設定します（後述）
LOGIN_URL = "https://www.e-license.jp/el31/lOZqZKHC3uM-brGQYS-1OA%3D%3D"
USER_ID = os.environ.get("USER_ID")
PASSWORD = os.environ.get("PASSWORD")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# データ保存用のファイル名
DATA_FILE = "reservation_cache.json"
# ==========================================

def send_discord_notify(message):
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
    except:
        pass

def load_previous_slots():
    """保存された前回のデータを読み込む"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f)) # リストをセット(集合)に戻す
        except:
            return set()
    return set()

def save_current_slots(slots_set):
    """今回のデータをファイルに保存する"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        # セット(集合)はJSONにできないのでリストに変換して保存
        json.dump(list(slots_set), f, ensure_ascii=False, indent=2)

def get_available_slots():
    # GitHub Actions用のヘッドレス設定
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument("--window-size=1280,1024")

    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options
    )

    found_slots_set = set()

    try:
        driver.get(LOGIN_URL)
        time.sleep(3)

        driver.find_element(By.NAME, "studentId").send_keys(USER_ID)
        driver.find_element(By.NAME, "password").send_keys(PASSWORD)
        
        try:
            driver.find_element(By.ID, "login").click()
        except:
            driver.find_element(By.XPATH, "//input[@value='ログイン']").click()
            
        time.sleep(5)

        # 空き状況取得
        open_slots_elements = driver.find_elements(By.CLASS_NAME, "status1")
        
        if len(open_slots_elements) > 0:
            for element in open_slots_elements:
                try:
                    if not element.is_displayed():
                        continue
                    link = element.find_element(By.TAG_NAME, "a")
                    info = f"{link.get_attribute('data-date')}{link.get_attribute('data-week')} {link.get_attribute('data-time')}"
                    found_slots_set.add(info)
                except:
                    pass

    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()
    
    return found_slots_set

if __name__ == "__main__":
    print("Checking...")
    
    # 1. 前回のデータを読み込み
    previous_slots = load_previous_slots()
    
    # 2. 今回のデータを取得
    current_slots = get_available_slots()
    
    # 3. 差分を計算 (今回 - 前回)
    new_added_slots = current_slots - previous_slots

    # 4. 通知判定
    if len(new_added_slots) > 0:
        print(f"New slots found: {len(new_added_slots)}")
        msg = f"@here 🎉 **{len(new_added_slots)}件** の新規空き枠が出ました！\n\n"
        for slot in new_added_slots:
            msg += f"🚗 **{slot}**\n"
        msg += f"\n[予約サイトへ]({LOGIN_URL})"
        send_discord_notify(msg)
    else:
        print("No new slots.")

    # 5. 今回の結果を保存 (次回のために上書き)
    # ※ 空きが減った場合も更新する必要があるため、常に保存します
    save_current_slots(current_slots)