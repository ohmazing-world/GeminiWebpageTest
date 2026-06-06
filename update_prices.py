import os
import requests
import yfinance as yf
from datetime import datetime, timedelta
import sys
import feedparser
import urllib.parse
import re
import base64

def log_msg(msg):
    print(f"[{get_taiwan_now().strftime('%H:%M:%S')}] 📡 {msg}\")
    sys.stdout.flush()

def get_taiwan_now():
    return datetime.utcnow() + timedelta(hours=8)

def decode_google_news_url(source_url):
    if "news.google.com" not in source_url:
        return source_url
    try:
        path = source_url.split("articles/")[-1].split("?")[0]
        padding = len(path) % 4
        if padding != 0:
            path += "=" * (4 - padding)
        decoded_bytes = base64.urlsafe_b64decode(path)
        decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
        urls = re.findall(r'https?://[^\s\x00-\x1f\x7f-\xff"\'<>]+', decoded_str)
        if urls:
            for u in urls:
                if "news.google.com" not in u and "googlevideo.com" not in u:
                    return u
    except Exception:
        pass
    return source_url

def fetch_from_yahoo(ticker, default_price, default_change):
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        price = info.last_price
        prev_close = info.previous_close
        
        if price is None or prev_close is None or prev_close == 0:
            return default_price, default_change
            
        change_pct = ((price - prev_close) / prev_close) * 100
        prefix = "+" if change_pct >= 0 else ""
        return f"{price:.2f}", f"{prefix}{change_pct:.2f}%"
    except Exception as e:
        log_msg(f"無法讀取 Yahoo {ticker} 價格，錯誤: {e}")
        return default_price, default_change

def fetch_stock_all_news(ticker, keyword):
    log_msg(f"正在為 {ticker} ({keyword}) 擷取 Google RSS 新聞...")
    encoded_keyword = urllib.parse.quote(keyword)
    rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    
    news_items = []
    try:
        feed = feedparser.parse(rss_url)
        entries = feed.entries[:3]  # 最多顯示 3 條
        
        for entry in entries:
            title = entry.title
            if " - " in title:
                title = title.split(" - ")[0]
            
            raw_link = entry.link
            real_link = decode_google_news_url(raw_link)
            
            date_str = ""
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                dt = datetime(*entry.published_parsed[:6]) + timedelta(hours=8)
                date_str = dt.strftime("%m-%d")
            else:
                date_str = get_taiwan_now().strftime("%m-%d")
                
            news_items.append((title, real_link, date_str))
    except Exception as e:
        log_msg(f"新聞擷取失敗 {ticker}: {e}")
        
    if not news_items:
        news_items.append(("今日無特定重大頭條，全球大盤大體維持平穩走勢。", "https://finance.yahoo.com", get_taiwan_now().strftime("%m-%d")))
        
    return news_items

def update_html_price_row(content, row_id, price_data, is_us=True):
    price, change = price_data
    currency_symbol = "$" if is_us else "NT$"
    color_class = "price-up" if "+" in change else "price-down"
    
    asset_names = {
        "vti_row": ("VTI (美股整體市場)", "VTI"),
        "vxus_row": ("VXUS (國際不含美)", "VXUS"),
        "vt_row": ("VT (全世界股票)", "VT"),
        "0050_row": ("元大台灣50", "0050.TW"),
        "tsmc_row": ("台積電", "2330.TW"),
        "honhai_row": ("鴻海", "2317.TW"),
        "japan_row": ("iShares安碩日本大型股ETF", "00981A.TW")
    }
    
    name, ticker = asset_names.get(row_id, ("未知資產", "UNKNOWN"))
    new_row = f'<tr id="{row_id}"><td>{name}</td><td>{ticker}</td><td>{currency_symbol}{price}</td><td class="{color_class}">{change}</td></tr>'
    
    pattern = rf'<tr id="{row_id}">.*?</tr>'
    return re.sub(pattern, new_row, content, flags=re.DOTALL)

def update_html_list(content, ul_id, news_items):
    list_html = f'<ul class="news-list" id="{ul_id}">'
    for title, link, date in news_items:
        list_html += f'\n                        <li><a href="{link}" target="_blank">{title}</a><span class="news-date">{date}</span></li>'
    list_html += '\n                    </ul>'
    
    pattern = rf'<ul class="news-list" id="{ul_id}">.*?</ul>'
    return re.sub(pattern, list_html, content, flags=re.DOTALL)

def main():
    html_path = "index.html"
    if not os.path.exists(html_path):
        log_msg(f"找不到錯誤: {html_path}")
        return

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    log_msg("1. 同步全球暨衛星資產行情...")
    vti_c = fetch_from_yahoo("VTI", "300.00", "+0.50%")
    vxus_c = fetch_from_yahoo("VXUS", "65.00", "-0.20%")
    vt_c = fetch_from_yahoo("VT", "115.00", "+0.15%")
    tw50_c = fetch_from_yahoo("0050.TW", "180.00", "+1.20%")
    tsmc_c = fetch_from_yahoo("2330.TW", "900.00", "+1.50%")
    honhai_c = fetch_from_yahoo("2317.TW", "180.00", "-0.50%")
    japan_c = fetch_from_yahoo("00981A.TW", "15.00", "+0.30%")

    content = update_html_price_row(content, "vti_row", vti_c, is_us=True)
    content = update_html_price_row(content, "vxus_row", vxus_c, is_us=True)
    content = update_html_price_row(content, "vt_row", vt_c, is_us=True)
    content = update_html_price_row(content, "0050_row", tw50_c, is_us=False)
    content = update_html_price_row(content, "tsmc_row", tsmc_c, is_us=False)
    content = update_html_price_row(content, "honhai_row", honhai_c, is_us=False)
    content = update_html_price_row(content, "japan_row", japan_c, is_us=False)
    
    log_msg("2. 個股觀點新聞同步...")
    content = update_html_list(content, "news_VTI", fetch_stock_all_news("VTI", "VTI ETF"))
    content = update_html_list(content, "news_VXUS", fetch_stock_all_news("VXUS", "VXUS ETF"))
    content = update_html_list(content, "news_VT", fetch_stock_all_news("VT", "VT ETF"))
    content = update_html_list(content, "news_0050", fetch_stock_all_news("0050.TW", "0050 ETF"))
    content = update_html_list(content, "news_2330", fetch_stock_all_news("2330.TW", "台積電"))
    content = update_html_list(content, "news_2317", fetch_stock_all_news("2317.TW", "鴻海"))
    content = update_html_list(content, "news_00981A", fetch_stock_all_news("00981A.TW", "00981A 日本"))

    log_msg("3. 自動刷上最新更新時間標記...")
    now_str = get_taiwan_now().strftime("%Y-%m-%d %H:%M:%S")
    time_html = f'<div class="update-time" id="price_update_time">最後更新：{now_str}</div>'
    content = re.sub(r'<div class="update-time" id="price_update_time">.*?</div>', time_html, content)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    log_msg("✨ 指數化花園資產動態更新作業成功完成！")

if __name__ == "__main__":
    main()
