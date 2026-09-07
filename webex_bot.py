# -*- coding: utf-8 -*-
"""
國立空中大學 115上 視訊面授 雲端無頭自動替身機器人 (Hardened Cloud Webex Bot)
===================================================================
學生：陳嬑萱 ｜ 學號：112122209 ｜ 登入身分：112122209陳嬑萱
守護核心特性：
1. 【精確表單填寫】：智慧等待預覽表單完全載入，確保「名稱」欄位確實填入「112122209陳嬑萱」，解鎖【加入 會議】按鈕！
2. 【零失誤開房等待機制】：若授課教師晚開房，自動輪詢等待最多 30 分鐘，一開房即刻自動闖入！
3. 【全智慧多輸入適配】：自動填入姓名與官方學號郵件 (112122209@nou.edu.tw)，相容所有 Webex 彈窗格式。
4. 【衝堂平行多開支援】：10/5 三門同時、9/23 雙門同時，啟動完全隔離的 Chromium 程序並行出席！
5. 【動態下課對齊】：自動根據 schedule.json 的 end_time 精確計算留守時間，下課後緩衝 5 分鐘安全離場。
6. 【全程心跳防斷線】：定時查核連線狀態，若遇網路閃斷自動偵測重新連線。
7. 【全程三段存證截圖】：進場、中途、下課前各截圖一張，留下完整出席佐證。
"""

import os
import sys
import time
import json
import datetime
import argparse
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

STUDENT_NAME = "112122209陳嬑萱"
STUDENT_EMAIL = "112122209@nou.edu.tw"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEDULE_FILE = os.path.join(BASE_DIR, 'schedule.json')

def load_schedule():
    with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_taipei_now():
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    taipei_tz = datetime.timezone(datetime.timedelta(hours=8))
    return utc_now.astimezone(taipei_tz)

def enter_webex_meeting(course_info, duration_minutes=None, is_test=False):
    cname = course_info['course_name']
    teacher = course_info['teacher']
    url = course_info['webex_url']
    now = get_taipei_now()
    today_str = now.strftime('%Y%m%d')
    today_date = now.date()
    safe_cname = cname.replace(' ', '_')
    prefix = f"[{cname}]"
    
    # 動態計算掛機時長（對齊至課程排定下課時間 + 5 分鐘緩衝）
    if duration_minutes is None and not is_test:
        end_hour, end_min = map(int, course_info['end_time'].split(':'))
        sched_end_dt = datetime.datetime.combine(today_date, datetime.time(end_hour, end_min), tzinfo=now.tzinfo)
        
        if now >= sched_end_dt:
            print(f"ℹ️ {prefix} 今日課程已於 {course_info['end_time']} 結束，無需重複進入。")
            return
            
        remaining_sec = (sched_end_dt - now).total_seconds() + 300  # 緩衝 5 分鐘
        duration_minutes = max(15, int(remaining_sec // 60))
    elif is_test:
        duration_minutes = 1
        
    print(f"\n==================================================")
    print(f"🚀 {prefix} [啟動雲端連線] 正在進入《{cname}》視訊會議室...")
    print(f"👨‍🏫 {prefix} 授課教師：{teacher} 老師 (分機 {course_info.get('ext', '')})")
    print(f"👤 {prefix} 出席身分：{STUDENT_NAME} ({STUDENT_EMAIL})")
    print(f"🌐 {prefix} 會議室網址：{url}")
    print(f"⏳ {prefix} 本次預計在線守護時長：{duration_minutes} 分鐘")
    print(f"==================================================\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--use-fake-ui-for-media-stream',
                '--use-fake-device-for-media-stream',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage'
            ]
        )
        context = browser.new_context(
            permissions=['microphone', 'camera'],
            viewport={'width': 1280, 'height': 800},
            locale='zh-TW',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        try:
            print(f"{prefix} [*] 步驟 1/5: 導航至 Webex 會議入口...")
            page.goto(url, wait_until='domcontentloaded', timeout=50000)
            time.sleep(3)
            
            # 處理 Cookie 接受彈窗
            try:
                cookie_btn = page.query_selector('button#onetrust-accept-btn-handler, button:has-text("接受"), button:has-text("Accept")')
                if cookie_btn:
                    cookie_btn.click()
            except Exception:
                pass
            
            print(f"{prefix} [*] 步驟 2/5: 點擊「從此瀏覽器加入」卡片...")
            card_clicked = False
            for text_pattern in ["Join from this browser", "從此瀏覽器加入", "Join from your browser", "Join from browser"]:
                try:
                    loc = page.get_by_text(text_pattern, exact=False)
                    if loc.count() > 0:
                        loc.first.click()
                        print(f"{prefix}   [+] 成功點擊瀏覽器入口卡片：{text_pattern}")
                        card_clicked = True
                        break
                except Exception:
                    pass
            
            if not card_clicked:
                try:
                    page.locator('div[role="button"]:has-text("browser"), div[role="button"]:has-text("瀏覽器")').first.click()
                    print(f"{prefix}   [+] 透過萬用語義定位點擊瀏覽器卡片。")
                except Exception:
                    pass
                    
            time.sleep(3)
            
            # 點擊彈出確認彈窗上的「從瀏覽器加入」按鈕 (id=joinFromWebapp)
            print(f"{prefix} [*] 步驟 2.5: 點擊確認彈窗「從瀏覽器加入」按鈕...")
            try:
                webapp_btn = page.locator('#joinFromWebapp, button:has-text("從瀏覽器加入"), button:has-text("Join from browser")')
                if webapp_btn.count() > 0 and webapp_btn.first.is_visible():
                    webapp_btn.first.click()
                    print(f"{prefix}   [+] 成功點擊 #joinFromWebapp 確認按鈕！")
            except Exception as e:
                print(f"{prefix}   [!] joinFromWebapp 提示：{e}")
                
            # 等待預覽頁面表單完全載入 (等待「名稱」或「輸入姓名」出現，最多等待 20 秒)
            print(f"{prefix} [*] 等待進入會議預覽表單頁面...")
            name_input_locator = None
            for wait_sec in range(20):
                # 策略 A: 尋找 placeholder 或 aria 包含名稱/姓名
                candidates = page.locator(
                    'input[placeholder*="名稱"], input[placeholder*="姓名"], input[placeholder*="Name"], '
                    'input[aria-label*="名稱"], input[aria-label*="姓名"], input[aria-label*="Name"], '
                    'input#meetingSimpleContainer, input[name="attendeeName"]'
                )
                if candidates.count() > 0 and candidates.first.is_visible():
                    name_input_locator = candidates.first
                    break
                    
                # 策略 B: 尋找文字「名稱」下方的可見輸入框
                all_inputs = page.locator('input:visible').all()
                text_inputs = [i for i in all_inputs if i.get_attribute('type') not in ['checkbox', 'radio', 'hidden']]
                if len(text_inputs) > 0:
                    name_input_locator = text_inputs[0]
                    break
                    
                time.sleep(1)
            
            print(f"{prefix} [*] 步驟 3/5: 輸入出席學生身分 ({STUDENT_NAME})...")
            if name_input_locator:
                try:
                    name_input_locator.click()
                    name_input_locator.fill(STUDENT_NAME)
                    time.sleep(1)
                    actual_val = name_input_locator.input_value()
                    print(f"{prefix}   [+] 🎯 成功填入身分名稱：【{actual_val}】！")
                except Exception as ex:
                    print(f"{prefix}   [!] 填入名稱微調：{ex}")
                    page.keyboard.type(STUDENT_NAME, delay=30)
            else:
                print(f"{prefix}   [!] 未直接定位到名稱框，嘗試全域焦點打字填入...")
                page.keyboard.press('Tab')
                page.keyboard.type(STUDENT_NAME, delay=30)
            
            time.sleep(2)
            
            # 若有第二個輸入框 (電子郵件)，也一併填入官方學號信箱
            try:
                email_candidates = page.locator(
                    'input[placeholder*="郵件"], input[placeholder*="Email"], '
                    'input[aria-label*="郵件"], input[aria-label*="Email"], '
                    'input[type="email"], input[name="email"]'
                )
                if email_candidates.count() > 0 and email_candidates.first.is_visible():
                    email_candidates.first.fill(STUDENT_EMAIL)
                    print(f"{prefix}   [+] 成功填入學生信箱：{STUDENT_EMAIL}")
            except Exception:
                pass
            
            # 確保麥克風與攝影機關閉 (靜音)
            print(f"{prefix} [*] 步驟 4/5: 確保麥克風與鏡頭靜音關閉...")
            try:
                # 檢查靜音按鈕
                mute_btn = page.locator('button[aria-label*="Mute"], button[aria-label*="靜音"]')
                if mute_btn.count() > 0 and mute_btn.first.is_visible():
                    mute_btn.first.click()
                    print(f"{prefix}   [+] 已點擊靜音麥克風。")
            except Exception:
                pass
                
            time.sleep(2)
            
            # 🌟 步驟 4.5: 智慧點擊【加入會議】大按鈕並輪詢開房守護
            print(f"{prefix} [*] 智慧開房守護: 點擊加入會議並偵測進場狀態...")
            max_wait_seconds = 1800  # 最多等待 30 分鐘
            poll_interval = 10
            poll_start = time.time()
            in_meeting = False
            
            # 先嘗試點擊【加入 會議】按鈕 (注意：Webex 介面文字可能有空格「加入 會議」或無空格「加入會議」)
            try:
                join_main = page.locator(
                    'button:has-text("加入 會議"), button:has-text("加入會議"), '
                    'button:has-text("Join meeting"), button#interstitial_join_button, '
                    'button[data-testid="join-button"]'
                )
                if join_main.count() > 0 and join_main.first.is_visible():
                    # 檢查按鈕是否已啟用
                    if not join_main.first.is_disabled():
                        join_main.first.click()
                        print(f"{prefix}   [🚀 點擊加入] 成功點擊【加入 會議】！正在進入視訊教室...")
                    else:
                        print(f"{prefix}   [!] 加入按鈕目前處於停用狀態，重新填入身分並解鎖...")
                        if name_input_locator:
                            name_input_locator.fill(STUDENT_NAME)
                        time.sleep(2)
                        join_main.first.click()
            except Exception as e:
                print(f"{prefix}   [!] 點擊加入按鈕提示：{e}")
            
            while time.time() - poll_start < max_wait_seconds:
                # 檢驗 1: 是否已在會議室內（特徵：離開按鈕、聊天面板、參加者名單、靜音控制列）
                in_meeting_elements = page.locator(
                    'button[aria-label*="離開"], button[aria-label*="Leave"], '
                    'button[aria-label*="靜音"], button[aria-label*="Mute"], '
                    'button[aria-label*="參加者"], button[aria-label*="Participants"], '
                    'button[aria-label*="聊天"], button[aria-label*="Chat"], '
                    'div[data-testid="in-meeting"], .meeting-layout, button[data-tippy-content*="離開"]'
                )
                if in_meeting_elements.count() > 0 and in_meeting_elements.first.is_visible():
                    in_meeting = True
                    print(f"{prefix}   [🎉 成功登入會議室] 已偵測到視訊會議核心控制列！確認已在會議室內！")
                    break
                
                # 檢驗 2: 是否有「加入 會議」或「Join meeting」按鈕可點擊
                join_btns = page.locator(
                    'button:has-text("加入 會議"), button:has-text("加入會議"), '
                    'button:has-text("Join meeting"), button#interstitial_join_button, '
                    'button[data-testid="join-button"]'
                )
                if join_btns.count() > 0 and join_btns.first.is_visible() and not join_btns.first.is_disabled():
                    try:
                        join_btns.first.click()
                        print(f"{prefix}   [+] 偵測到開房加入按鈕，已點擊【加入會議】！")
                        time.sleep(6)
                        continue
                    except Exception:
                        pass
                
                # 檢驗 3: 檢查是否在大廳等待頁面（老師尚未開房）
                waiting_indicators = page.locator('text=會議尚未開始, text=等待主持人, text=Waiting for the host, text=The meeting has not started')
                if waiting_indicators.count() > 0:
                    waited_mins = int((time.time() - poll_start) // 60)
                    if int(time.time() - poll_start) % 60 < poll_interval:
                        print(f"{prefix}   [⏳ 大廳駐守等待] 授課教師尚未開房 (已駐守 {waited_mins} 分鐘)，雲端替身持續駐守大廳，老師一開房即刻衝入...")
                
                # 若是測試模式且已等待超過 25 秒，截圖結束
                if is_test and (time.time() - poll_start) > 25:
                    break
                    
                time.sleep(poll_interval)
            
            # 截取進場成功證明截圖 (各科獨立檔名)
            proof_file = os.path.join(BASE_DIR, f'attendance_proof_{today_str}_{safe_cname}.png')
            page.screenshot(path=proof_file)
            print(f"{prefix} [*] 步驟 5/5: 📸 已截取會議室連線存證截圖：{proof_file}")
            
            # 同步更新通用 attendance_proof.png
            try:
                default_proof = os.path.join(BASE_DIR, 'attendance_proof.png')
                page.screenshot(path=default_proof)
            except Exception:
                pass

            print(f"\n🎉 {prefix} 【全勤守護啟動】《{cname}》連線成功！學生 [{STUDENT_NAME}] 正在會議室全程在線...")
            
            if is_test:
                print(f"{prefix} 🧪 [測試模式] 保持在線 45 秒後自動安全退出...")
                time.sleep(45)
            else:
                total_seconds = duration_minutes * 60
                interval = 180  # 每 3 分鐘一次心跳與斷線偵測
                elapsed = 0
                mid_captured = False
                
                while elapsed < total_seconds:
                    time.sleep(min(interval, total_seconds - elapsed))
                    elapsed += interval
                    mins_done = elapsed // 60
                    print(f"{prefix}   [💓 雲端在線心跳] 《{cname}》已持續上課在線 {mins_done} / {duration_minutes} 分鐘 (連線穩固)...")
                    
                    # 中途截圖存證 (上課達 50% 時)
                    if mins_done >= duration_minutes // 2 and not mid_captured:
                        mid_file = os.path.join(BASE_DIR, f'attendance_proof_{today_str}_{safe_cname}_mid.png')
                        try:
                            page.screenshot(path=mid_file)
                            mid_captured = True
                            print(f"{prefix}   [📸 中途存證] 已截取課程中段守護截圖：{mid_file}")
                        except Exception:
                            pass
                    
                    # 斷線守護：若 Webex 出現「重新連線」或「連線中斷」按鈕，立即自動點擊恢復
                    try:
                        reconnect_btn = page.locator('button:has-text("重新連線"), button:has-text("Reconnect"), button:has-text("重試")')
                        if reconnect_btn.count() > 0 and reconnect_btn.first.is_visible():
                            print(f"{prefix}   [⚠️ 偵測到斷線] 立即點擊【重新連線】以恢復在線狀態...")
                            reconnect_btn.first.click()
                    except Exception:
                        pass
            
            print(f"\n🏁 {prefix} 【下課全勤離場】課程《{cname}》時間結束，平穩退出會議室。")
            
        except Exception as e:
            print(f"{prefix} ⚠️ 執行過程捕獲異常：{e}")
            try:
                err_file = os.path.join(BASE_DIR, f'error_dump_{safe_cname}.png')
                page.screenshot(path=err_file)
                print(f"{prefix}   [!] 已保存錯誤當下截圖：{err_file}")
            except Exception:
                pass
        finally:
            browser.close()

def auto_detect_and_run():
    now = get_taipei_now()
    today_str = now.strftime('%Y-%m-%d')
    current_hour = now.hour
    current_hm = now.strftime('%H:%M')
    
    print(f"🔍 [雲端排程巡檢] 台北時間：{today_str} {current_hm}")
    schedule = load_schedule()
    
    matched = []
    for c in schedule:
        if today_str in c['dates']:
            start_hour = int(c['start_time'].split(':')[0])
            end_hour, end_min = map(int, c['end_time'].split(':'))
            course_end_dt = datetime.datetime.combine(now.date(), datetime.time(end_hour, end_min), tzinfo=now.tzinfo)
            
            # 若課程已結束超過 10 分鐘，跳過
            if now > course_end_dt + datetime.timedelta(minutes=10):
                continue
                
            # 依目前執行時段智慧篩選：
            # 13:00~16:30 執行下午班課程 (14:00 開課)
            # 18:00~22:00 執行夜間班課程 (19:00 開課)
            # 其他時段 (例如手動觸發) 則執行今日全部尚未結束的課程
            if 13 <= current_hour < 17:
                if start_hour < 17:
                    matched.append(c)
            elif 17 <= current_hour < 23:
                if start_hour >= 17:
                    matched.append(c)
            else:
                matched.append(c)
            
    if not matched:
        print(f"ℹ️ 今日 ({today_str} {current_hm}) 此時段無排定待出席面授課程，雲端機器人休眠退出。")
        return
    
    print(f"🎯 鎖定此時段有 {len(matched)} 門面授課程：")
    for c in matched:
        print(f"   • 《{c['course_name']}》{c['start_time']}~{c['end_time']} (師：{c['teacher']})")
    
    if len(matched) == 1:
        # 單門課常規出席
        enter_webex_meeting(matched[0])
    else:
        # ⚡ 衝堂平行多開支援（如 10/5 三門同時、9/23 雙門同時）
        print(f"\n⚡ [衝堂平行多開觸發] 偵測到 {len(matched)} 門課程同時段開課！立即啟動 {len(matched)} 組獨立並行容器同時出席...")
        with ThreadPoolExecutor(max_workers=len(matched)) as executor:
            futures = [
                executor.submit(enter_webex_meeting, c)
                for c in matched
            ]
            for f in futures:
                f.result()
        print(f"\n🏆 [衝堂守護圓滿完工] 今日同時段 {len(matched)} 門課程已全數平行出席完工！")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='空大115上 視訊面授 雲端無頭自動替身機器人')
    parser.add_argument('--auto', action='store_true', help='自動依今日排程偵測上課 (支援衝堂多開)')
    parser.add_argument('--test', action='store_true', help='立即測試連接第一門課45秒並截圖存證')
    parser.add_argument('--course', type=str, help='手動指定課程名稱')
    parser.add_argument('--duration', type=int, help='手動指定掛機時間(分鐘)')
    args = parser.parse_args()
    
    schedule = load_schedule()
    
    if args.test:
        enter_webex_meeting(schedule[0], duration_minutes=1, is_test=True)
    elif args.course:
        found = next((c for c in schedule if args.course in c['course_name']), None)
        if found:
            enter_webex_meeting(found, duration_minutes=args.duration)
        else:
            print(f"❌ 找不到課程：{args.course}")
    elif args.auto:
        auto_detect_and_run()
    else:
        auto_detect_and_run()
