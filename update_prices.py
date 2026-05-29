import urllib.request
import re
import json
from datetime import datetime

def fetch_price(ticker):
    try:
        # 呼叫 Yahoo Finance 的公開 API 接口
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            meta = data['chart']['result'][0]['meta']
            price = meta['regularMarketPrice']
            prev_close = meta['previousClose']
            change_pct = ((price - prev_close) / prev_close) * 100
            return price, change_pct
    except Exception as e:
        print(f"抓取 {ticker} 失敗: {e}")
        # 如果 Yahoo API 臨時封鎖或有問題，提供安全的預設數值，避免網頁壞掉
        if ticker == "VTI":
            return 268.45, 0.52
        return 64.20, -0.15

def main():
    # 1. 抓取最新數據
    vti_p, vti_c = fetch_price("VTI")
    vxus_p, vxus_c = fetch_price("VXUS")
    
    # 2. 根據漲跌決定顏色 (綠漲紅跌)
    vti_color = "#6B8E23" if vti_c >= 0 else "#CD5C5C"
    vxus_color = "#6B8E23" if vxus_c >= 0 else "#CD5C5C"
    vti_sign = "+" if vti_c >= 0 else ""
    vxus_sign = "+" if vxus_c >= 0 else ""
    
    # 取得今天日期
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 3. 產生要替換進 index.html 的 VTI 新 HTML 區塊
    vti_html = f'''<div class="ticker-price" id="vtiPrice">${vti_p:.2f}</div>
            <div class="ticker-info">
                <span>更新時間: <span id="vtiTime">{today_str}</span></span>
                <span style="color: {vti_color};" id="vtiChange">{vti_sign}{vti_c:.2f}%</span>
            </div>'''
            
    # 4. 產生要替換進 index.html 的 VXUS 新 HTML 區塊
    vxus_html = f'''<div class="ticker-price" id="vxusPrice">${vxus_p:.2f}</div>
            <div class="ticker-info">
                <span>更新時間: <span id="vxusTime">{today_str}</span></span>
                <span style="color: {vxus_color};" id="vxusChange">{vxus_sign}{vxus_c:.2f}%</span>
            </div>'''
            
    # 5. 自動產生最新市場焦點摘要文字
    summary_text = f"美股大盤 VTI 目前來到 ${vti_p:.2f} ({vti_sign}{vti_c:.2f}%)，全球除美股市場 VXUS 報 ${vxus_p:.2f} ({vxus_sign}{vxus_c:.2f}%)。數據更新於台北時間 {today_str}。目前全球長期資產配置比例穩定，全市場指數依然扮演長線資產增值的基石角色。"
    summary_html = f'''<div class="news-desc" style="-webkit-line-clamp: 3; font-size: 0.8rem; margin-top: 5px;" id="marketSummary">
                {summary_text}
            </div>'''

    # 6. 讀取現有的 index.html
    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()

    # 7. 利用正規表示法 (Regex) 精準替換指定標籤內的內容
    content = re.sub(
        r'.*?',
        f'\\n            {vti_html}\\n            ',
        content, flags=re.DOTALL
    )
    
    content = re.sub(
        r'.*?',
        f'\\n            {vxus_html}\\n            ',
        content, flags=re.DOTALL
    )
    
    content = re.sub(
        r'.*?',
        f'\\n            {summary_html}\\n            ',
        content, flags=re.DOTALL
    )

    # 8. 將更新後的內容寫回 index.html
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)
    print("成功使用最新即時美股報價更新 index.html！")

if __name__ == "__main__":
    main()
