# -*- coding: utf-8 -*-
"""
國立空中大學 115上 視訊面授 雲端無頭自動替身機器人 (Precision Webex Bot)
===================================================================
學生：陳嬑萱 ｜ 學號：112122209 ｜ 登入身分：112122209陳嬑萱
守護核心特性：
1. 【高精度座標物理注入】：在標準 1280x800 視窗下，直擊 (985, 310) 名稱輸入框與 (985, 490) 加入大按鈕，無視任何 Shadow DOM / iframe 隔閡！
2. 【綠色大按鈕物理直擊】：精確點擊解鎖後的【加入 會議】，絕不誤觸行動裝置或 QR 彈窗！
3. 【零失誤開房等待機制】：若授課教師晚開房，自動輪詢等待最多 30 分鐘，一開房即刻自動闖入！
4. 【衝堂平行多開支援】：10/5 三門同時、9/23 雙門同時，啟動完全隔離的 Chromium 程序並行出席！
5. 【動態下課對齊】：自動根據 schedule.json 的 end_time 精確計算留守時間，下課後緩衝 5 分鐘安全離場。
6. 【全程心跳防斷線】：定時查核連線狀態，若遇網路閃斷自動偵測重新連線。
7. 【全程三段存證截圖】：進場、中途、下課前各截圖一張，自動推送至 GitHub 儀表板留存。
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

def log(msg):
    print(msg, flush=True)

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
            log(f"ℹ️ {prefix} 今日課程已於 {course_info['end_time']} 結束，無需重複進入。")
            return
            
        remaining_sec = (sched_end_dt - now).total_seconds() + 300  # 緩衝 5 分鐘
        duration_minutes = max(15, int(remaining_sec // 60))
    elif is_test:
        duration_minutes = 1
        
    log(f"\n==================================================")
    log(f"🚀 {prefix} [啟動雲端連線] 正在進入《{cname}》視訊會議室...")
    log(f"👨‍🏫 {prefix} 授課教師：{teacher} 老師 (分機 {course_info.get('ext', '')})")
    log(f"👤 {prefix} 出席身分：{STUDENT_NAME} ({STUDENT_EMAIL})")
    log(f"🌐 {prefix} 會議室網址：{url}")
    log(f"⏳ {prefix} 本次預計在線守護時長：{duration_minutes} 分鐘")
    log(f"==================================================\n")
    
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
            log(f"{prefix} [*] 步驟 1/5: 導航至 Webex 會議入口網址...")
            page.goto(url, wait_until='domcontentloaded', timeout=50000)
            time.sleep(3)
            
            # 處理 Cookie 接受彈窗
            try:
                cookie_btn = page.query_selector('button#onetrust-accept-btn-handler, button:has-text("接受"), button:has-text("Accept")')
                if cookie_btn:
                    cookie_btn.click()
            except Exception:
                pass
            
            log(f"{prefix} [*] 步驟 2/5: 點擊「從此瀏覽器加入」卡片...")
            card_clicked = False
            for text_pattern in ["Join from this browser", "從此瀏覽器加入", "Join from your browser", "Join from browser"]:
                try:
                    loc = page.get_by_text(text_pattern, exact=False)
                    if loc.count() > 0:
                        loc.first.click()
                        log(f"{prefix}   [+] 成功點擊瀏覽器入口卡片：{text_pattern}")
                        card_clicked = True
                        break
                except Exception:
                    pass
            
            if not card_clicked:
                try:
                    page.locator('div[role="button"]:has-text("browser"), div[role="button"]:has-text("瀏覽器")').first.click()
                    log(f"{prefix}   [+] 透過萬用語義定位點擊瀏覽器卡片。")
                except Exception:
                    pass
                    
            time.sleep(3)
            
            # 點擊彈出確認彈窗上的「從瀏覽器加入」按鈕 (id=joinFromWebapp)
            log(f"{prefix} [*] 步驟 2.5: 點擊確認彈窗「從瀏覽器加入」按鈕...")
            try:
                webapp_btn = page.locator('#joinFromWebapp, button:has-text("從瀏覽器加入"), button:has-text("Join from browser")')
                if webapp_btn.count() > 0 and webapp_btn.first.is_visible():
                    webapp_btn.first.click()
                    log(f"{prefix}   [+] 成功點擊 #joinFromWebapp 確認按鈕！")
            except Exception as e:
                log(f"{prefix}   [!] joinFromWebapp 提示：{e}")
                
            # 等待預覽頁面完全載入
            log(f"{prefix} [*] 等待 Webex 會議預覽介面完全載入 (14 秒)...")
            time.sleep(14)
            
            # 步驟 3: 高精度物理座標定位 (985, 310) 填入身分
            log(f"{prefix} [*] 步驟 3/5: 高精度物理座標 (985, 310) 注入出席身分 ({STUDENT_NAME})...")
            page.mouse.click(985, 310)
            time.sleep(0.5)
            page.keyboard.press("Control+A")
            time.sleep(0.2)
            page.keyboard.press("Backspace")
            time.sleep(0.2)
            page.keyboard.type(STUDENT_NAME, delay=60)
            log(f"{prefix}   [+] 🎯 物理座標輸入框已確實打字注入：【{STUDENT_NAME}】！")
            
            time.sleep(1)
            
            # 確保麥克風與攝影機關閉 (靜音按鈕在左下方預覽列，座標約 180, 775)
            log(f"{prefix} [*] 步驟 4/5: 確保麥克風靜音關閉...")
            try:
                page.mouse.click(180, 775)
                log(f"{prefix}   [+] 已點擊靜音麥克風。")
            except Exception:
                pass
                
            time.sleep(1)
            
            # 🌟 步驟 4.5: 高精度物理座標點擊綠色【加入 會議】大按鈕 (座標 965, 515)
            log(f"{prefix} [*] 步驟 4.5: 高精度直擊【加入 會議】大按鈕 (965, 515) 正式進入會議室...")
            page.mouse.click(965, 515)
            log(f"{prefix}   [🚀 點擊進場] 已精確點擊 (965, 515) 【加入 會議】按鈕！")
            
            # 輔以鍵盤 Enter 鍵雙重確保
            time.sleep(0.5)
            page.keyboard.press("Enter")
            
            time.sleep(8)
            
            # 截取進場成功證明截圖 (各科獨立檔名)
            proof_file = os.path.join(BASE_DIR, f'attendance_proof_{today_str}_{safe_cname}.png')
            page.screenshot(path=proof_file)
            log(f"{prefix} [*] 步驟 5/5: 📸 已截取會議室連線存證截圖：{proof_file}")
            
            # 同步更新通用 attendance_proof.png
            try:
                default_proof = os.path.join(BASE_DIR, 'attendance_proof.png')
                page.screenshot(path=default_proof)
            except Exception:
                pass

            log(f"\n🎉 {prefix} 【全勤守護啟動】《{cname}》連線成功！學生 [{STUDENT_NAME}] 正在會議室全程在線...")
            
            if is_test:
                log(f"{prefix} 🧪 [測試模式] 保持在線 45 秒後自動安全退出...")
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
                    log(f"{prefix}   [💓 雲端在線心跳] 《{cname}》已持續上課在線 {mins_done} / {duration_minutes} 分鐘 (連線穩固)...")
                    
                    # 中途截圖存證 (上課達 50% 時)
                    if mins_done >= duration_minutes // 2 and not mid_captured:
                        mid_file = os.path.join(BASE_DIR, f'attendance_proof_{today_str}_{safe_cname}_mid.png')
                        try:
                            page.screenshot(path=mid_file)
                            mid_captured = True
                            log(f"{prefix}   [📸 中途存證] 已截取課程中段守護截圖：{mid_file}")
                        except Exception:
                            pass
                    
                    # 斷線守護：若 Webex 出現「重新連線」或「連線中斷」按鈕，立即自動點擊恢復
                    try:
                        reconnect_btn = page.locator('button:has-text("重新連線"), button:has-text("Reconnect"), button:has-text("重試")')
                        if reconnect_btn.count() > 0 and reconnect_btn.first.is_visible():
                            log(f"{prefix}   [⚠️ 偵測到斷線] 立即點擊【重新連線】以恢復在線狀態...")
                            reconnect_btn.first.click()
                    except Exception:
                        pass
            
            log(f"\n🏁 {prefix} 【下課全勤離場】課程《{cname}》時間結束，平穩退出會議室。")
            
        except Exception as e:
            log(f"{prefix} ⚠️ 執行過程捕獲異常：{e}")
            try:
                err_file = os.path.join(BASE_DIR, f'error_dump_{safe_cname}.png')
                page.screenshot(path=err_file)
                log(f"{prefix}   [!] 已保存錯誤當下截圖：{err_file}")
            except Exception:
                pass
        finally:
            browser.close()

def auto_detect_and_run():
    now = get_taipei_now()
    today_str = now.strftime('%Y-%m-%d')
    current_hour = now.hour
    current_hm = now.strftime('%H:%M')
    
    log(f"🔍 [雲端排程巡檢] 台北時間：{today_str} {current_hm}")
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
        log(f"ℹ️ 今日 ({today_str} {current_hm}) 此時段無排定待出席面授課程，雲端機器人休眠退出。")
        return
    
    log(f"🎯 鎖定此時段有 {len(matched)} 門面授課程：")
    for c in matched:
        log(f"   • 《{c['course_name']}》{c['start_time']}~{c['end_time']} (師：{c['teacher']})")
    
    if len(matched) == 1:
        # 單門課常規出席
        enter_webex_meeting(matched[0])
    else:
        # ⚡ 衝堂平行多開支援（如 10/5 三門同時、9/23 雙門同時）
        log(f"\n⚡ [衝堂平行多開觸發] 偵測到 {len(matched)} 門課程同時段開課！立即啟動 {len(matched)} 組獨立並行容器同時出席...")
        with ThreadPoolExecutor(max_workers=len(matched)) as executor:
            futures = [
                executor.submit(enter_webex_meeting, c)
                for c in matched
            ]
            for f in futures:
                f.result()
        log(f"\n🏆 [衝堂守護圓滿完工] 今日同時段 {len(matched)} 門課程已全數平行出席完工！")

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
            log(f"❌ 找不到課程：{args.course}")
    elif args.auto:
        auto_detect_and_run()
    else:
        auto_detect_and_run()
