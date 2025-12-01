from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import time
import requests
import os

# ==========================================
# 設定エリア
# ==========================================
LOGIN_URL = "https://www.e-license.jp/el31/lOZqZKHC3uM-brGQYS-1OA%3D%3D"

USER_ID = os.environ["USER_ID"]
PASSWORD = os.environ["PASSWORD"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
CHECK_INTERVAL = 600 # 10分
# ==========================================

def send_discord_notify(message):
    """Discordにメッセージを送信する関数"""
    if not DISCORD_WEBHOOK_URL:
        print("! Webhook URLが設定されていないため通知をスキップしました。")
        return

    data = {"content": message}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=data)
        # 成功(204)以外の場合はエラーを表示
        if response.status_code not in [200, 204]:
             print(f"Discord通知エラー: {response.status_code} - {response.text}")
        else:
             print("Discordに通知を送信しました")
    except Exception as e:
        print(f"送信時にエラーが発生しました: {e}")

def get_available_slots():
    """
    ログインして空き状況を取得し、セット（集合）として返す関数
    戻り値: {"12月2日(火) 13:50", "12月2日(火) 14:50", ...}
    """
    print("\n--------------------------------")
    print(f"チェックを開始します...{time.strftime('%Y-%m-%d %H:%M:%S')}")
    # send_discord_notify(f"チェックを開始します  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    options = webdriver.ChromeOptions()
    options.add_argument('--headless') 
    
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options
    )

    found_slots_set = set() # 今回見つけた枠を入れる集合

    try:
        # 1. ログイン
        driver.get(LOGIN_URL)
        time.sleep(3)

        driver.find_element(By.NAME, "studentId").send_keys(USER_ID)
        driver.find_element(By.NAME, "password").send_keys(PASSWORD)
        
        try:
            driver.find_element(By.ID, "login").click()
        except:
            driver.find_element(By.XPATH, "//input[@value='ログイン']").click()
            
        time.sleep(5) 

        # 4. 空き状況の収集
        open_slots_elements = driver.find_elements(By.CLASS_NAME, "status1")
        
        if len(open_slots_elements) > 0:
            for element in open_slots_elements:
                try:
                    if not element.is_displayed():
                        continue

                    link_tag = element.find_element(By.TAG_NAME, "a")
                    
                    date_val = link_tag.get_attribute("data-date") 
                    week_val = link_tag.get_attribute("data-week") 
                    time_val = link_tag.get_attribute("data-time") 
                    
                    slot_info = f"{date_val}{week_val} {time_val}"
                    
                    # 集合(set)に追加（setなら自動で重複が排除されます）
                    found_slots_set.add(slot_info)
                        
                except Exception as e:
                    pass
        
        # ログ用：現在の総数を表示
        if len(found_slots_set) > 0:
            print(f"現在の空き枠数: {len(found_slots_set)}枠")
        else:
            print("空きなし")

    except Exception as e:
        print(f"! エラー発生: {e}")
        # エラー時は空のセットを返して安全に終了
        return set()

    finally:
        try:
            driver.quit()
        except:
            pass
    
    return found_slots_set

# ==========================================
# メインループ
# ==========================================
if __name__ == "__main__":
    print(f"監視を開始します。（間隔: {CHECK_INTERVAL}秒）")
    
    # ★ポイント: 前回の結果を覚えておく変数
    previous_slots = set()

    while True:
        # 1. 現在の空き枠を取得
        current_slots = get_available_slots()
        
        # 2. 差分検知（今回あるもの - 前回あったもの = 新しく増えたもの）
        # ※Pythonの set(集合) は引き算ができます
        new_added_slots = current_slots - previous_slots

        # 3. 新しい枠があれば通知
        if len(new_added_slots) > 0:
            print("\n" + "="*30)
            print(f"新しい予約枠が {len(new_added_slots)}件 追加されました！")
            print("="*30)
            
            msg_body = ""
            for slot in new_added_slots:
                line = f"・{slot}"
                print(line)
                msg_body += line + "\n"

            # ★将来ここにDiscord通知のコードを書きます
            send_discord_notify(msg_body)
            
        elif len(current_slots) > 0:
            # 空きはあるけど、前回と変わっていない場合
            print("空き枠はありますが、新規追加はありません。")
        
        # 4. 次回のために「今回の結果」を「前回」として保存
        previous_slots = current_slots

        print(f"次回チェックまで {CHECK_INTERVAL}秒 待機します...")
        time.sleep(CHECK_INTERVAL)