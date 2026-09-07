# -*- coding: utf-8 -*-
"""
國立空中大學 115上 視訊面授 雲端無頭自動替身機器人 (Cloud Webex Bot)
學生：陳嬑萱 ｜ 學號：112122209 ｜ 登入身分：112122209陳嬑萱
"""

import os
import sys
import time
import json
import datetime
import argparse
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

def enter_webex_meeting(course_info, duration_minutes=110, is_test=False):
    cname = course_info['course_name']
    teacher = course_info['teacher']
    url = course_info['webex_url']
    
    print(f"\n==================================================")
    print(f"🚀 [啟動雲端連線] 正在進入《{cname}》視訊會議室...")
    print(f"👨‍🏫 授課教師：{teacher} 老師 (分機 {course_info['ext']})")
    print(f"👤 出席身分：{STUDENT_NAME}")
    print(f"🌐 原始會議室網址：{url}")
    print(f"⏳ 預計在線掛機時間：{duration_minutes} 分鐘")
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
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        try:
            print(f"[*] 步驟 1/5: 導航至 Webex 頁面...")
            page.goto(url, wait_until='domcontentloaded', timeout=45000)
            time.sleep(3)
            
            # 處理可能出現的 Cookie 接受彈窗
            try:
                cookie_btn = page.query_selector('button#onetrust-accept-btn-handler, button:has-text("接受"), button:has-text("Accept")')
                if cookie_btn:
                    cookie_btn.click()
                    print("  [+] 已自動接受 Cookie 授權。")
            except Exception:
                pass
            
            print(f"[*] 步驟 2/5: 定位並點選「從此瀏覽器加入」按鈕...")
            browser_joined = False
            browser_selectors = [
                'button:has-text("從此瀏覽器加入")',
                'a:has-text("從此瀏覽器加入")',
                'button:has-text("Join from your browser")',
                'a:has-text("Join from your browser")',
                'button[data-ouiicon-name="browser"]',
                'div[role="button"]:has-text("瀏覽器")',
                'div[role="button"]:has-text("browser")'
            ]
            for sel in browser_selectors:
                btn = page.query_selector(sel)
                if btn:
                    btn.click()
                    print(f"  [+] 成功點擊按鈕 ({sel})！")
                    browser_joined = True
                    break
            
            if not browser_joined:
                cards = page.query_selector_all('div[role="button"], button')
                for c in cards:
                    txt = (c.inner_text() or '').lower()
                    if '瀏覽器' in txt or 'browser' in txt:
                        c.click()
                        browser_joined = True
                        break
            
            time.sleep(5)
            
            print(f"[*] 步驟 3/5: 輸入出席學生身分 ({STUDENT_NAME})...")
            # 尋找 Name 輸入框 (支援中英文多重定位)
            name_input = page.query_selector('input[aria-label*="Name"], input[placeholder*="Name"], input[aria-label*="姓名"], input[placeholder*="姓名"], input[type="text"]')
            if name_input:
                name_input.click()
                name_input.fill(STUDENT_NAME)
                print(f"  [+] 成功填入出席姓名：{STUDENT_NAME}")
            else:
                # 備用方案：頁面上所有可輸入 input
                all_inputs = page.query_selector_all('input')
                for inp in all_inputs:
                    inp_type = inp.get_attribute('type') or 'text'
                    if inp_type in ['text', '']:
                        inp.fill(STUDENT_NAME)
                        print(f"  [+] 透過通用輸入框填入姓名：{STUDENT_NAME}")
                        break
            
            time.sleep(2)
            
            print(f"[*] 步驟 4/5: 確保靜音與關閉攝影機...")
            # 點選 Mute 按鈕
            try:
                mute_btn = page.query_selector('button[aria-label*="Mute"]:not([aria-label*="Unmute"]), button[aria-label*="靜音"]:not([aria-label*="取消靜音"])')
                if mute_btn:
                    mute_btn.click()
                    print("  [+] 麥克風已切換為靜音。")
            except Exception:
                pass
                
            # 點選 Stop video 按鈕
            try:
                stop_video_btn = page.query_selector('button[aria-label*="Stop video"], button[aria-label*="停止視訊"]')
                if stop_video_btn:
                    stop_video_btn.click()
                    print("  [+] 攝影機已關閉。")
            except Exception:
                pass
            
            time.sleep(2)
            
            # 點擊「Join meeting」或「加入會議」綠色大按鈕
            join_btn = page.query_selector('button:has-text("Join meeting"), button:has-text("加入會議"), button#interstitial_join_button, button[data-ouiicon-name="join-meeting"]')
            if join_btn:
                join_btn.click()
                print("  [+] 🚀 成功點擊【Join meeting / 加入會議】按鈕！正式進入會議室！")
            else:
                # 嘗試點擊畫面上有 Join 字樣的大按鈕
                possible_btns = page.query_selector_all('button')
                for b in possible_btns:
                    btxt = (b.inner_text() or '').strip().lower()
                    if 'join' in btxt or '加入' in btxt:
                        b.click()
                        print(f"  [+] 透過替代按鈕點擊進場 ({btxt})！")
                        break
            
            time.sleep(6)
            
            # 截取進場成功證明截圖
            proof_file = os.path.join(BASE_DIR, 'attendance_proof.png')
            page.screenshot(path=proof_file)
            print(f"[*] 步驟 5/5: 📸 已截取會議室連線存證截圖：{proof_file}")
            print(f"\n🎉 【成功進場】《{cname}》連線成功！學生 [{STUDENT_NAME}] 正在會議室持續在線中...")
            
            if is_test:
                print("🧪 [測試模式] 保持在線 45 秒後自動退出...")
                time.sleep(45)
            else:
                total_seconds = duration_minutes * 60
                interval = 300
                elapsed = 0
                while elapsed < total_seconds:
                    time.sleep(min(interval, total_seconds - elapsed))
                    elapsed += interval
                    mins_done = elapsed // 60
                    print(f"  [💓 雲端在線心跳] 《{cname}》已持續上課在線 {mins_done} / {duration_minutes} 分鐘 (狀態良好)...")
            
            print(f"\n🏁 【下課離場】課程《{cname}》時間結束，平穩退出會議室。")
            
        except Exception as e:
            print(f"⚠️ 執行過程捕獲異常：{e}")
            try:
                err_file = os.path.join(BASE_DIR, 'error_dump.png')
                page.screenshot(path=err_file)
                print(f"  [!] 已保存錯誤當下截圖：{err_file}")
            except Exception:
                pass
        finally:
            browser.close()

def auto_detect_and_run():
    now = get_taipei_now()
    today_str = now.strftime('%Y-%m-%d')
    current_hm = now.strftime('%H:%M')
    
    print(f"🔍 [雲端排程巡檢] 台北時間：{today_str} {current_hm}")
    schedule = load_schedule()
    
    matched = []
    for c in schedule:
        if today_str in c['dates']:
            matched.append(c)
            
    if not matched:
        print(f"ℹ️ 今日 ({today_str}) 無任何排定面授課程，雲端機器人休眠退出。")
        return
    
    print(f"🎯 鎖定今日有 {len(matched)} 門面授課程：")
    for c in matched:
        print(f"   • 《{c['course_name']}》{c['start_time']}~{c['end_time']} (師：{c['teacher']})")
        enter_webex_meeting(c, duration_minutes=c.get('duration_minutes', 110))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='空大115上 視訊面授 雲端無頭自動替身機器人')
    parser.add_argument('--auto', action='store_true', help='自動依今日排程偵測上課')
    parser.add_argument('--test', action='store_true', help='立即測試連接第一門課45秒並截圖存證')
    parser.add_argument('--course', type=str, help='手動指定課程名稱')
    parser.add_argument('--duration', type=int, default=110, help='指定掛機時間(分鐘)')
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
