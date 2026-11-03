# -*- coding: utf-8 -*-
"""
OS201 期中考午夜自動守護與試題下載腳本
科目：作業系統的理論基礎 (林秀鳳 老師)
開放時間：2026-10-30 00:00:00 ~ 2026-11-02 23:59:59
"""
import os
import sys
import json
import time
import re
import urllib.parse
import datetime
import requests
import urllib3

urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

SESSION_FILE = r'C:\Users\manpo\Downloads\nou_active_session.json'
DESKTOP_DIR = r'C:\Users\manpo\OneDrive\桌面\作業系統的理論基礎'
D_DIR = r'D:\02_Academic_Study\空大課程\作業系統的理論基礎'
CID = '10053349'

def load_session():
    if not os.path.exists(SESSION_FILE):
        raise FileNotFoundError(f"找不到憑證檔案: {SESSION_FILE}")
    with open(SESSION_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def init_requests():
    sess_data = load_session()
    s = requests.Session()
    s.verify = False
    for k, v in sess_data['cookies'].items():
        s.cookies.set(k, v, domain='uu.nou.edu.tw')
        s.cookies.set(k, v, domain='.nou.edu.tw')
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://uu.nou.edu.tw/learn/index.php'
    })
    return s, sess_data['pTicket']

def switch_to_os(s, pTicket):
    req_xml = f'<manifest><ticket>{pTicket}</ticket><course_id>{CID}</course_id></manifest>'
    r = s.post('https://uu.nou.edu.tw/learn/goto_course.php', data=req_xml.encode('utf-8'), timeout=15)
    return r.status_code == 200

def check_and_fetch():
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] 🔍 正在向 SunNet LMS 檢查《作業系統的理論基礎》期中考上傳區...")
    
    s, pTicket = init_requests()
    switch_to_os(s, pTicket)
    
    r = s.get('https://uu.nou.edu.tw/learn/homework/homework_list.php', timeout=15)
    if '期中考' not in r.text:
        print("⚠️ 頁面未發現『期中考』關鍵字，可能連線超時或未正確切換課程。")
        return False
        
    pos = r.text.find('期中考上傳繳交區')
    if pos == -1:
        print("⚠️ 未找到『期中考上傳繳交區』")
        return False
        
    start = r.text.rfind('<div class="box', 0, pos)
    end = r.text.find('<div class="box', pos)
    if end == -1: end = len(r.text)
    block = r.text[start:end]
    
    calls = re.findall(r"view_homework\(['\"]homework['\"],\s*['\"]([^'\"]+)['\"]", block)
    
    print(f"  • 期中考狀態區塊已鎖定 (長度: {len(block)} 字元)")
    
    if calls:
        eid = calls[0]
        print(f"🎉 偵測到期中考作業已開放作答！EID: {eid}")
        
        turnin_url = f"https://uu.nou.edu.tw/learn/homework/homework_turnin.php?{eid}"
        r_detail = s.get(turnin_url, timeout=15)
        
        attachments = re.findall(r'href=[\"\']([^\"\']*(?:\.docx|\.pdf|\.doc|\.zip|\.odt|\.txt)[^\"\']*)[\"\']', r_detail.text, re.IGNORECASE)
        
        save_exam_content(r_detail.text)
        
        if attachments:
            for att in set(attachments):
                full_url = urllib.parse.urljoin('https://uu.nou.edu.tw/learn/homework/', att)
                fname = os.path.basename(att.split('?')[0])
                if not fname: fname = "os_midterm_paper.docx"
                print(f"📥 發現考題附件: {fname} -> 立即下載...")
                r_file = s.get(full_url, timeout=30)
                if r_file.status_code == 200:
                    for target_dir in [DESKTOP_DIR, D_DIR]:
                        target_path = os.path.join(target_dir, fname)
                        with open(target_path, 'wb') as f_out:
                            f_out.write(r_file.content)
                        print(f"  ✅ 附件已成功存入: {target_path}")
        return True
    else:
        print("⏳ 目前尚未到達開放時間（2026-10-30 00:00）。系統按鈕目前處於鎖定倒數狀態。")
        print("   預定開放區間：2026-10-30 00:00 到 2026-11-02 23:59")
        return False

def save_exam_content(html_text):
    clean_text = re.sub(r'<script[^>]*>.*?</script>', '', html_text, flags=re.DOTALL)
    clean_text = re.sub(r'<style[^>]*>.*?</style>', '', clean_text, flags=re.DOTALL)
    clean_text = re.sub(r'<[^>]+>', ' ', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    doc = f"""# 📝 《作業系統的理論基礎》期中考題目全文與說明
> 擷取時間：{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> 官方作業項目：期中考上傳繳交區 (佔 30%)

## 📋 官方頁面文字內容
{clean_text}
"""
    for d in [DESKTOP_DIR, D_DIR]:
        path = os.path.join(d, "期中考考題全文與題型說明.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(doc)
    print("✅ 題目網頁說明已同步儲存至桌面與 D 槽！")

if __name__ == '__main__':
    try:
        check_and_fetch()
    except Exception as e:
        print(f"❌ 執行發生異常: {e}")
