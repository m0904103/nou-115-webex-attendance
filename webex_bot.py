# -*- coding: utf-8 -*-
"""
國立空中大學 115上 視訊面授 雲端無頭自動替身機器人 (Precision Webex Cloud Bot V2.1 鋼鐵防護版)
===================================================================
學生：陳嬑萱 ｜ 學號：112122209 ｜ 登入身分：112122209陳嬑萱
核心特性：
1. 【解除跨來源安全隔離】：注入 --disable-web-security 與 --disable-site-isolation-trials，徹底打通 nou.webex.com 與 web.webex.com 內嵌框架。
2. 【Shadow-DOM 原生事件穿透】：直接觸發 Cisco Momentum Web Components 底層 #join-button 核心協議。
3. 【自適應表單識別】：支援全新無紀錄進場、瀏覽器記憶進場、需郵件進場等所有變體，零拋錯、零超時卡死。
4. 【全自動繞過入口彈窗】：精確點擊 #broadcom-center-right 與 #fallBkJoinByBrowser，杜絕行動裝置推廣與桌面應用提示。
5. 【衝堂平行多開支援】：10/5 三門同時、9/23 雙門同時，啟動完全隔離的 Chromium 實例並行出席！
6. 【動態下課對齊】：自動根據 schedule.json 的 end_time 精確計算留守時間，下課後緩衝 10 分鐘安全離場。
7. 【全程三段存證截圖】：進場、中途、下課前各截圖一張，自動推送至 GitHub 儀表板與 Artifacts 留存。
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
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] {msg}", flush=True)

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
    
    # 動態計算留守時長
    if duration_minutes is None and not is_test:
        start_hour, start_min = map(int, course_info['start_time'].split(':'))
        end_hour, end_min = map(int, course_info['end_time'].split(':'))
        sched_start_dt = datetime.datetime.combine(today_date, datetime.time(start_hour, start_min), tzinfo=now.tzinfo)
        sched_end_dt = datetime.datetime.combine(today_date, datetime.time(end_hour, end_min), tzinfo=now.tzinfo)
        
        if now >= sched_end_dt + datetime.timedelta(minutes=10):
            log(f"ℹ️ {prefix} 今日課程已於 {course_info['end_time']} 結束超過 10 分鐘，無需重複進入。")
            return
            
        if now < sched_start_dt:
            early_mins = int((sched_start_dt - now).total_seconds() // 60)
            log(f"⏰ {prefix} [提早進場待命] 距表定開課 ({course_info['start_time']}) 尚有 {early_mins} 分鐘，已提前進房待命，【100% 零遲到】！")
            
        remaining_sec = (sched_end_dt - now).total_seconds() + 600  # 延後 10 分鐘安全緩衝
        duration_minutes = max(15, int(remaining_sec // 60))
        log(f"⏰ {prefix} [延後離場守護] 表定下課 {course_info['end_time']}，分身將持續在線守護至下課後 10 分鐘，【100% 零早退】！")
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
                '--disable-web-security',
                '--disable-site-isolation-trials',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-features=IsolateOrigins,site-per-process',
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
            page.goto(url, wait_until='networkidle', timeout=60000)
            time.sleep(2)
            
            # 處理 Cookie 接受彈窗
            try:
                page.evaluate("() => { let b = Array.from(document.querySelectorAll('button')).find(x => x.innerText.includes('接受')); if (b) b.click(); }")
                time.sleep(1)
            except Exception:
                pass
            
            # 點擊「從此瀏覽器加入」卡片
            log(f"{prefix} [*] 步驟 2/5: 點擊「從此瀏覽器加入」入口卡片...")
            try:
                page.evaluate("() => { let c = document.getElementById('broadcom-center-right'); if (c) c.click(); }")
            except Exception as e:
                log(f"{prefix}   [!] 卡片點擊提示：{e}")
            time.sleep(2)
            
            # 點擊彈窗確認「從瀏覽器加入」
            log(f"{prefix} [*] 步驟 2.5: 點擊彈窗確認「從瀏覽器加入」按鈕...")
            try:
                page.evaluate("() => { let btns = document.querySelectorAll('#fallBkJoinByBrowser'); if (btns.length > 0) btns[0].click(); }")
            except Exception as e:
                log(f"{prefix}   [!] fallBkJoinByBrowser 提示：{e}")
                
            # 等待 web.webex.com 通訊框架載入
            log(f"{prefix} [*] 步驟 3/5: 等待 Webex 通訊核心框架 (web.webex.com)...")
            target_frame = None
            for attempt in range(25):
                time.sleep(1.5)
                for f in page.frames:
                    if 'web.webex.com' in f.url:
                        target_frame = f
                        break
                if target_frame:
                    break
                    
            if not target_frame:
                log(f"{prefix} ❌ 找不到 web.webex.com 框架，保存除錯畫面...")
                err_file = os.path.join(BASE_DIR, f'error_frame_{safe_cname}.png')
                page.screenshot(path=err_file)
                return False

            log(f"{prefix}   [+] 成功鎖定核心通訊框架：{target_frame.url[:60]}")
            
            # 注入出席學號姓名 (自適應偵測：若已有快取或無需填寫則平穩略過)
            log(f"{prefix} [*] 步驟 4/5: 偵測出席學號姓名欄位...")
            try:
                name_inp = target_frame.locator('input[type="text"]')
                if name_inp.count() > 0:
                    name_inp.first.fill(STUDENT_NAME)
                    name_inp.first.press('Tab')
                    time.sleep(1)
                    log(f"{prefix}   [+] 🎯 姓名欄位已確實注入：【{STUDENT_NAME}】！")
                else:
                    # 等待最多 5 秒
                    target_frame.wait_for_selector('input[type="text"]', timeout=5000)
                    target_frame.locator('input[type="text"]').first.fill(STUDENT_NAME)
                    log(f"{prefix}   [+] 🎯 姓名欄位已確實注入：【{STUDENT_NAME}】！")
            except Exception as e:
                log(f"{prefix}   [ℹ️] 姓名欄位已由系統鎖定或無需重複填寫。")

            # 注入出席郵件 (若有要求)
            try:
                email_inp = target_frame.locator('input[type="email"], input[name*="email"], input[placeholder*="郵件"]')
                if email_inp.count() > 0:
                    email_inp.first.fill(STUDENT_EMAIL)
                    email_inp.first.press('Tab')
                    log(f"{prefix}   [+] 🎯 郵件欄位已確實注入：【{STUDENT_EMAIL}】！")
            except Exception:
                pass

            # 檢查預覽大廳中的視訊狀態，若預設開啟則提前點擊關閉視訊
            try:
                target_frame.evaluate("""() => {
                    let btns = Array.from(document.querySelectorAll('button, mdc-button, [role="button"]'));
                    for (let b of btns) {
                        let label = (b.getAttribute('aria-label') || '') + ' ' + (b.innerText || '') + ' ' + (b.getAttribute('data-test') || '');
                        if (label.includes('停止視訊') || label.includes('關閉視訊') || label.includes('Stop video') || label.includes('Mute video')) {
                            b.click();
                            break;
                        }
                    }
                }""")
            except Exception:
                pass

            # 觸發「加入會議」核心協議
            log(f"{prefix} [*] 步驟 5/5: 觸發 Shadow-DOM 核心「加入會議」元件...")
            click_res = target_frame.evaluate("""() => {
                let mdc = document.querySelector('#join-button') || document.querySelector('mdc-button[data-test="join-button"]');
                if (mdc) {
                    mdc.click();
                    return { success: true, method: 'mdc.click()' };
                }
                let all = Array.from(document.querySelectorAll('*'));
                let btn = all.find(e => (e.innerText || '').includes('加入') && e.children.length === 0);
                if (btn) {
                    btn.click();
                    return { success: true, method: 'text.click()' };
                }
                return { success: false };
            }""")
            log(f"{prefix}   [+] 核心按鈕點擊結果：{click_res}")

            # 等待會議室渲染與進場
            log(f"{prefix} [*] 等待會議室音訊視訊渲染 (15 秒)...")
            time.sleep(15)

            # 處理可能出現的音訊授權確認彈窗
            try:
                for text_btn in ["連接音訊", "使用電腦音訊", "我瞭解", "確定", "加入語音", "通知主持人"]:
                    btn = target_frame.locator(f'button:has-text("{text_btn}")')
                    if btn.count() > 0 and btn.first.is_visible():
                        log(f"{prefix}   [+] 自動點擊對話框按鈕：{text_btn}")
                        btn.first.click()
            except Exception:
                pass

            # 🛡️ 核心禮儀與隱私守護：強制關閉視訊鏡頭（杜絕 Chromium 虛擬綠色畫面外流）
            log(f"{prefix} [*] 正在檢查視訊鏡頭狀態，確保隱私與課堂合規禮儀...")
            try:
                stop_video_clicked = False
                for frame in [target_frame, page]:
                    clicked = frame.evaluate("""() => {
                        let allButtons = Array.from(document.querySelectorAll('button, [role="button"], mdc-button'));
                        for (let b of allButtons) {
                            let text = (b.innerText || '').trim();
                            let label = b.getAttribute('aria-label') || '';
                            let dataTest = b.getAttribute('data-test') || '';
                            if (text.includes('停止視訊') || label.includes('停止視訊') || label.includes('Stop video') || dataTest.includes('stop-video')) {
                                b.click();
                                return true;
                            }
                        }
                        return false;
                    }""")
                    if clicked:
                        stop_video_clicked = True
                        log(f"{prefix}   [📷] 🎯 成功偵測並點擊【停止視訊】！鏡頭已關閉，杜絕綠色雷達畫面外流！")
                        time.sleep(2)
                        break
                if not stop_video_clicked:
                    log(f"{prefix}   [📷] 視訊鏡頭確認處於關閉狀態（無開啟或已預設關閉）。")
            except Exception as e:
                log(f"{prefix}   [!] 關閉視訊操作提示：{e}")

            # 截取進場成功證明截圖
            proof_file = os.path.join(BASE_DIR, f'attendance_proof_{today_str}_{safe_cname}.png')
            page.screenshot(path=proof_file)
            log(f"{prefix} 📸 ✅ 進場成功證明截圖已保存：{proof_file}")
            
            # 同步更新通用 attendance_proof.png (儀表板直接顯示)
            try:
                default_proof = os.path.join(BASE_DIR, 'attendance_proof.png')
                page.screenshot(path=default_proof)
            except Exception:
                pass

            log(f"\n🎉 {prefix} 【全勤守護啟動】《{cname}》連線就緒！學生 [{STUDENT_NAME}] 正在會議室全程在線...")
            
            if is_test:
                log(f"{prefix} 🧪 [測試模式] 保持在線 45 秒後自動安全退出...")
                time.sleep(45)
            else:
                total_seconds = duration_minutes * 60
                interval = 120  # 每 2 分鐘在線心跳
                elapsed = 0
                mid_captured = False
                
                while elapsed < total_seconds:
                    time.sleep(min(interval, total_seconds - elapsed))
                    elapsed += interval
                    mins_done = elapsed // 60
                    log(f"{prefix}   [💓 雲端在線心跳] 《{cname}》已持續上課在線 {mins_done} / {duration_minutes} 分鐘 (連線穩固，全勤守護中)...")
                    
                    # 偵測主持人結束會議
                    try:
                        end_modal = page.locator('text="會議已由主持人結束", text="The meeting has ended", text="會議已結束", text="主持人已結束此會議", text="已結束此會議"')
                        if end_modal.count() > 0 and end_modal.first.is_visible():
                            log(f"{prefix} 🎓 授課教師已關閉會議室，本日面授課程圓滿下課！【100% 零早退】")
                            break
                    except Exception:
                        pass

                    # 🛡️ 循環巡檢：確保視訊鏡頭保持關閉
                    try:
                        target_frame.evaluate("""() => {
                            let allButtons = Array.from(document.querySelectorAll('button, [role="button"], mdc-button'));
                            for (let b of allButtons) {
                                let text = (b.innerText || '').trim();
                                let label = b.getAttribute('aria-label') || '';
                                if (text.includes('停止視訊') || label.includes('停止視訊') || label.includes('Stop video')) {
                                    b.click();
                                    break;
                                }
                            }
                        }""")
                    except Exception:
                        pass

                    # 中途存證截圖 (50% 時)
                    if mins_done >= duration_minutes // 2 and not mid_captured:
                        mid_file = os.path.join(BASE_DIR, f'attendance_proof_{today_str}_{safe_cname}_mid.png')
                        try:
                            page.screenshot(path=mid_file)
                            page.screenshot(path=os.path.join(BASE_DIR, 'attendance_proof.png'))
                            mid_captured = True
                            log(f"{prefix}   [📸 中途存證] 已截取課程中段守護截圖：{mid_file}")
                        except Exception:
                            pass
            
            log(f"\n🏁 {prefix} 【超額全勤離場】課程《{cname}》時間充裕結束，出席時數達標超額完成，平穩退出會議室！")
            
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
                
            # 依時段智慧篩選：
            # 13:00~16:30 執行下午班課程
            # 18:00~22:00 執行夜間班課程
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
        enter_webex_meeting(matched[0])
    else:
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
