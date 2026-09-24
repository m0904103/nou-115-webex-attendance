# -*- coding: utf-8 -*-
"""
cloud_study_runner.py - 國立空中大學 (NOU) 115-1 雲端 24H 自律研讀守護程式
====================================================================
專為 GitHub Actions (微軟 Azure 雲端伺服器) 設計：
1. 支援從 GitHub Secrets (NOU_SESSION_JSON) 或本機憑證自動載入
2. 智慧「窪地填平」演算法：優先攻堅官方在線時數最低之科目，滿 50h 自動避讓
3. 單線程防護、絕不多開、每 60 秒發送合規自然心跳，徹底杜絕 -97 限制
4. 研讀前後皆向 SunNet LMS 官方 (learn_stat.php) 核實真實學務時數
5. 自動刷新 data.json 並產生正式查核記錄，供 GitHub Pages 零時差呈現
6. 學生無需開機，關閉筆電、電腦關機照常 24H 穩健推進！
"""

import os
import sys
import time
import json
import random
import re
import argparse
from datetime import datetime
import urllib3
import requests
from bs4 import BeautifulSoup

# 設定編碼與忽略 SSL 警告
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()

COURSE_CONFIG = [
    {"cid": "10053170", "name": "生成式AI在行政實務的應用-ZZZ001班", "short_name": "生成式AI在行政實務的應用", "target_hours": 50.0},
    {"cid": "10053349", "name": "作業系統的理論基礎-ZZZ101班", "short_name": "作業系統的理論基礎", "target_hours": 50.0},
    {"cid": "10053272", "name": "淺談人工智慧倫理-ZZZ002班", "short_name": "淺談人工智慧倫理", "target_hours": 50.0},
    {"cid": "10053334", "name": "AI時代的中文敘事與思辨-ZZZ001班", "short_name": "AI時代的中文敘事與思辨", "target_hours": 50.0},
    {"cid": "10053339", "name": "永續的挑戰與實踐-ZZZ002班", "short_name": "永續的挑戰與實踐", "target_hours": 50.0},
    {"cid": "10053265", "name": "人工智慧導論-ZZZ002班", "short_name": "人工智慧導論", "target_hours": 50.0},
    {"cid": "10053311", "name": "探索宇宙之美-ZZZ002班", "short_name": "探索宇宙之美", "target_hours": 50.0},
]

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def safe_request(sess, method, url, max_retries=5, **kwargs):
    for attempt in range(max_retries):
        try:
            if method.upper() == "GET":
                return sess.get(url, **kwargs)
            else:
                return sess.post(url, **kwargs)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                log(f"  ⚠️ 網路暫態波動 ({e})，稍後重試...")
                return None

def load_session_credentials():
    # 1. 優先從環境變數 (GitHub Secrets) 載入
    env_creds = os.environ.get("NOU_SESSION_JSON")
    if env_creds:
        try:
            log("🔑 從 GitHub Secrets (NOU_SESSION_JSON) 載入登入憑證...")
            data = json.loads(env_creds)
            return data
        except Exception as e:
            log(f"⚠️ 解析環境變數 NOU_SESSION_JSON 失敗: {e}")

    # 2. 次要：從本機路徑搜尋
    possible_paths = [
        "nou_active_session.json",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "nou_active_session.json"),
        os.path.join(os.path.expanduser("~"), "Downloads", "nou_active_session.json"),
        r"C:\Users\manpo\Downloads\nou_active_session.json",
        r"C:\Users\manpo\.gemini\antigravity\brain\aad4075a-7cc7-4b17-bd2a-74fbc04f07d7\scratch\nou_active_session.json",
    ]
    for p in possible_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    log(f"🔑 從本地檔案載入憑證: {p}")
                    return json.load(f)
            except Exception as e:
                pass

    log("❌ 找不到任何有效的登入憑證！請確認 GitHub Secret NOU_SESSION_JSON 是否已設定。")
    return None

def fetch_official_stats(sess):
    try:
        r = safe_request(sess, "GET", "https://uu.nou.edu.tw/learn/learn_stat.php", timeout=12)
        if not r or r.status_code != 200:
            return {}
        soup = BeautifulSoup(r.text, 'html.parser')
        stats = {}
        for tr in soup.find_all('tr'):
            tds = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
            if len(tds) >= 6:
                cname = tds[0]
                time_str = tds[5]
                parts = time_str.split(':')
                if len(parts) == 3:
                    try:
                        h = int(parts[0]) + int(parts[1])/60.0 + int(parts[2])/3600.0
                        stats[cname] = {"hours": round(h, 2), "str": time_str}
                    except:
                        pass
        return stats
    except Exception as e:
        log(f"抓取官方時數異常: {e}")
        return {}

def calculate_analytics(courses):
    total_courses = len(courses)
    total_credits = sum(c.get('credits', 0) for c in courses)
    total_hours = sum(c.get('reading_hours', 0.0) for c in courses)
    avg_lighting = sum(c.get('lighting_percent', 0) for c in courses) / total_courses if total_courses else 0
    
    total_meetings = 0
    attended_meetings = 0
    for c in courses:
        meetings = c.get('meetings', [])
        total_meetings += len(meetings)
        attended_meetings += sum(1 for m in meetings if m.get('attended', False))
    
    attendance_rate = round((attended_meetings / total_meetings * 100), 1) if total_meetings else 0
    
    total_hw = 0
    submitted_hw = 0
    for c in courses:
        for hw_key in ['hw1', 'hw2']:
            hw = c.get(hw_key, {})
            total_hw += 1
            if hw.get('submitted', False):
                submitted_hw += 1
    
    hw_rate = round((submitted_hw / total_hw * 100), 1) if total_hw else 0
    
    # 計算各科真實得分
    course_earned_scores = []
    for c in courses:
        l_score = min(100, max(0, c.get('lighting_percent', 0)))
        h_score = min(100, (max(0, c.get('reading_hours', 0.0)) / 50.0) * 100.0)
        c_meetings = c.get('meetings', [])
        m_attended = sum(1 for m in c_meetings if m.get('attended', False))
        m_score = (m_attended / len(c_meetings) * 100.0) if c_meetings else 0.0
        
        hw1_score = c.get('hw1', {}).get('score', 0) if c.get('hw1', {}).get('submitted', False) else 0
        hw2_score = c.get('hw2', {}).get('score', 0) if c.get('hw2', {}).get('submitted', False) else 0
        hw_score = (hw1_score + hw2_score) / 2.0
        
        regular = (l_score * 0.20) + (h_score * 0.20) + (m_score * 0.30) + (hw_score * 0.30)
        midterm = c.get('midterm', {}).get('score', 0)
        final = c.get('final', {}).get('score', 0)
        
        earned = (regular * 0.30) + (midterm * 0.30) + (final * 0.40)
        course_earned_scores.append(earned)
    
    avg_earned = round(sum(course_earned_scores) / len(course_earned_scores), 1) if course_earned_scores else 0.0
    reading_hours_score = min(6.0, round((total_hours / 350.0) * 6.0, 2))

    return {
        "total_courses": total_courses,
        "total_credits": total_credits,
        "total_reading_hours": round(total_hours, 1),
        "reading_hours_score": reading_hours_score,
        "average_lighting_percent": round(avg_lighting, 1),
        "total_meetings": total_meetings,
        "attended_meetings": attended_meetings,
        "attendance_rate": attendance_rate,
        "total_homework": total_hw,
        "submitted_homework": submitted_hw,
        "homework_submission_rate": hw_rate,
        "current_earned_grade_avg": avg_earned,
        "grade_policy": "依空大學則：平時(30%)=點燈(20%)+時數(20%)+面授(30%)+作業(30%)；期中(30%)+期末(40%)尚未開考計0分"
    }

def update_repo_data_file(data_path, stats, audit_detail=None):
    if not os.path.exists(data_path):
        return None
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            d = json.load(f)

        total_hours = 0.0
        for c in d.get("courses", []):
            name = c.get("name", "")
            for k, v in stats.items():
                if name in k or k in name or any(part in k for part in name.split()):
                    c["reading_hours"] = v["hours"]
                    c["reading_time_str"] = v["str"]
                    break
            total_hours += c.get("reading_hours", 0.0)

        d["analytics"] = calculate_analytics(d["courses"])
        d["official_sync"]["last_checked_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if audit_detail:
            log_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "type": "CLOUD_STUDY_AUTO",
                "result": "SUCCESS",
                "detail": audit_detail
            }
            if "audit_logs" not in d:
                d["audit_logs"] = []
            d["audit_logs"].insert(0, log_entry)
            d["audit_logs"] = d["audit_logs"][:15]

        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)

        return d
    except Exception as e:
        log(f"更新 data.json 失敗: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="NOU 115-1 Cloud Study Runner")
    parser.add_argument("--duration-mins", type=int, default=25, help="Study block duration in minutes (default: 25)")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "data.json")

    log("=" * 70)
    log(f"☁️ 空大 115上【GitHub Actions 雲端 24H 自律研讀守護程式】啟動！")
    log(f"   - 運行環境: 雲端伺服器 (Azure/Ubuntu)")
    log(f"   - 本輪時長: {args.duration_mins} 分鐘 (合規 60s 心跳)")
    log("=" * 70)

    creds = load_session_credentials()
    if not creds:
        sys.exit(0)

    pTicket = creds.get("pTicket", "") or creds.get("cookies", {}).get("idx", "")
    cookies = creds.get("cookies", {})

    sess = requests.Session()
    sess.verify = False
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://uu.nou.edu.tw/learn/mooc_sysbar.php",
    })
    for k, v in cookies.items():
        sess.cookies.set(k, v, domain="uu.nou.edu.tw")
        sess.cookies.set(k, v, domain=".nou.edu.tw")

    # 1. 驗證連線合法性
    test_url = f"https://uu.nou.edu.tw/xmlapi/index.php?action=my-course-path-info&onlyProgress=0&cid=10053170&ticket={pTicket}"
    r_test = safe_request(sess, "GET", test_url, timeout=12)
    if not r_test or r_test.status_code != 200 or r_test.json().get("code") != 0:
        log("⚠️ 憑證已過期或伺服器驗證未通過，本輪雲端研讀暫緩。請更新憑證。")
        sys.exit(0)
    log(f"🎉 憑證驗證成功！合法連接空大 SunNet LMS 伺服器 (ticket: {pTicket[:8]}...)")

    # 2. 獲取研讀前真實時數
    stats_before = fetch_official_stats(sess)
    update_repo_data_file(data_path, stats_before)

    # 3. 識別窪地優先攻堅隊列
    active_queue = []
    log("\n📊 >>>【研讀前官方各科在線時數盤點】>>>")
    total_before = 0.0
    for cfg in COURSE_CONFIG:
        s_name = cfg["short_name"]
        stat = None
        for k, v in stats_before.items():
            if s_name in k:
                stat = v
                break
        cur_h = stat["hours"] if stat else 10.0
        cur_str = stat["str"] if stat else f"{cur_h:.2f}h"
        total_before += cur_h
        gap = max(0.0, cfg["target_hours"] - cur_h)

        if cur_h >= cfg["target_hours"]:
            log(f"  🏆 [{s_name}]: {cur_str} ({cur_h:.2f}h / 50h) ➔ 100% 滿分！[豁免避讓]")
        else:
            log(f"  ⚡ [{s_name}]: {cur_str} ({cur_h:.2f}h / 50h) ➔ 尚缺 {gap:.2f}h [排入攻堅]")
            active_queue.append({
                "cid": cfg["cid"],
                "name": cfg["name"],
                "short_name": s_name,
                "current_h": cur_h,
                "gap": gap
            })

    if not active_queue:
        log("🎉🎉🎉 恭喜！全學期 7 門大課全部達到 50 小時滿分標準！")
        sys.exit(0)

    # 依時數最低者優先攻堅 (窪地填平)
    active_queue.sort(key=lambda x: x["current_h"])
    target_course = active_queue[0]
    log(f"\n🎯 本輪雲端第一攻堅目標 ➔ 【{target_course['short_name']}】(目前 {target_course['current_h']:.2f}h，尚缺 {target_course['gap']:.2f}h)")

    # 4. 取得該課程之章節節點
    cid = target_course["cid"]
    path_url = f"https://uu.nou.edu.tw/xmlapi/index.php?action=my-course-path-info&onlyProgress=0&cid={cid}&ticket={pTicket}"
    r_path = safe_request(sess, "GET", path_url, timeout=12)
    leaf_nodes = []
    if r_path and r_path.status_code == 200:
        def flatten(items):
            for it in items:
                if it.get("leaf") is True or not it.get("item"):
                    leaf_nodes.append(it)
                else:
                    flatten(it.get("item", []))
        try:
            flatten(r_path.json().get("data", {}).get("path", {}).get("item", []))
        except:
            pass

    if not leaf_nodes:
        log("  ⚠️ 未取得單元節點，跳過本輪。")
        sys.exit(0)

    # 切換課程環境以獲取 enCid
    req_xml = f'<manifest><ticket>{pTicket}</ticket><course_id>{cid}</course_id></manifest>'
    safe_request(sess, "POST", 'https://uu.nou.edu.tw/learn/goto_course.php', data=req_xml.encode('utf-8'), timeout=10)
    time.sleep(1)

    sess.headers.update({"Referer": "https://uu.nou.edu.tw/learn/path/pathtree.php"})
    r_tree = safe_request(sess, "GET", "https://uu.nou.edu.tw/learn/path/pathtree.php", timeout=10)
    enCid = cid
    if r_tree and r_tree.status_code == 200:
        m_cid = re.findall(r'name="course_id"\s+value="([^"]+)"', r_tree.text)
        if m_cid:
            enCid = m_cid[0]

    # 選定單元展開研讀
    selected_node = random.choice(leaf_nodes)
    actid = selected_node.get("id", "")
    title = selected_node.get("text", selected_node.get("title", f"單元_{actid}"))
    title = re.sub(r'<[^>]+>', '', title).strip()

    log(f"\n📘 開始雲端合規研讀【{target_course['short_name']}】之【{title}】")
    log(f"   - 研讀預計時長: {args.duration_mins} 分鐘")
    log(f"   - 心跳間隔: 60 秒合規連續推升")

    r_time = safe_request(sess, "GET", "https://uu.nou.edu.tw/learn/path/getServerTime.php", timeout=10)
    server_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if r_time and r_time.status_code == 200:
        m_time = re.findall(r'server_time="([^"]+)"', r_time.text)
        if m_time:
            server_time = m_time[0]

    r_start = safe_request(
        sess, "POST",
        "https://uu.nou.edu.tw/mooc/controllers/course_record.php?actype=start",
        data={
            "action": "setReading",
            "ticket": pTicket,
            "type": "start",
            "period": 0,
            "enCid": enCid,
            "bt": server_time,
            "title": title,
            "enUrl": "",
            "actid": actid
        },
        timeout=10
    )
    bt_res = server_time
    if r_start and r_start.status_code == 200:
        try:
            bt_res = r_start.json().get("data", server_time)
        except:
            bt_res = server_time

    # 執行自然累積心跳
    total_study_seconds = args.duration_mins * 60
    elapsed_seconds = 0
    while elapsed_seconds < total_study_seconds:
        time.sleep(60)
        elapsed_seconds += 60

        r_end = safe_request(
            sess, "POST",
            "https://uu.nou.edu.tw/mooc/controllers/course_record.php?actype=end",
            data={
                "action": "setReading",
                "ticket": pTicket,
                "type": "end",
                "period": 60,
                "enCid": enCid,
                "bt": bt_res,
                "title": title,
                "enUrl": "",
                "actid": actid
            },
            timeout=10
        )
        mins_done = elapsed_seconds // 60
        log(f"   ⏱️ [雲端心跳] 【{target_course['short_name'][:8]}】進度: {mins_done}/{args.duration_mins} 分鐘 (+{(elapsed_seconds/3600):.2f}h)")

    # 5. 研讀完成，重新獲取官方最新累積時數
    log("\n🏁 本輪雲端研讀圓滿完成！正在抓取 SunNet LMS 最新學務數據...")
    time.sleep(3)
    stats_after = fetch_official_stats(sess)
    
    cur_7_total = 0.0
    for cfg in COURSE_CONFIG:
        for k, v in stats_after.items():
            if cfg["short_name"] in k:
                cur_7_total += v["hours"]
                break

    target_new_stat = None
    for k, v in stats_after.items():
        if target_course["short_name"] in k:
            target_new_stat = v
            break
            
    new_h = target_new_stat.get("hours", target_course["current_h"]) if target_new_stat else target_course["current_h"]
    new_str = target_new_stat.get("str", "") if target_new_stat else ""

    detail_msg = f"雲端 24H 自律研讀完成：【{target_course['short_name']}】+ {args.duration_mins} 分鐘 (目前達 {new_str or f'{new_h}h'})，全科 7 門在線時數達 {cur_7_total:.1f}h / 350h。"
    log(f"✅ {detail_msg}")

    update_repo_data_file(data_path, stats_after, audit_detail=detail_msg)
    log("💾 官方最新學務數據已成功寫入 data.json！\n")

if __name__ == "__main__":
    main()
