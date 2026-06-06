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
    print(f"[{get_taiwan_now().strftime('%H:%M:%S')}] 📡 {msg}")
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
        if price is not None and prev_close is not None and prev_close != 0:
            change_pct = ((price - prev_close) / prev_close) * 100
            return price, change_pct
    except Exception as e:
        log_msg(f"Yahoo Finance 抓取失敗 ({ticker}): {e}")
    return default_price, default_change

def fetch_stock_all_news(ticker, display_name):
    log_msg(f"開始抓取 RSS 新聞: {display_name} ({ticker})")
    enc_name = urllib.parse.quote(display_name)
    rss_url = f"https://news.google.com/rss/search?q={enc_name}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    
    html_snippets = []
    try:
        feed = feedparser.parse(rss_url)
        items = feed.entries[:8]
        if not items:
            log_msg(f"⚠️ {display_name} 查無任何新聞項目。")
            return f"<li class='news-item'>暫無最新相關新聞動態。</li>"
            
        for entry in items:
            title = entry.title
            if " - " in title:
                title = " - ".join(title.split(" - ")[:-1])
            raw_link = entry.link
            link = decode_google_news_url(raw_link)
            source = entry.get('source', {}).get('text', '網路新聞')
            
            pub_ts = entry.get('published_parsed')
            if pub_ts:
                dt = datetime(*pub_ts[:6]) + timedelta(hours=8)
                time_str = dt.strftime("%m-%d %H:%M")
            else:
                time_str = get_taiwan_now().strftime("%m-%d %H:%M")
                
            html_snippets.append(
                f"<li class='news-item'>"
                f"<a href='{link}' target='_blank'>{title}</a>"
                f"<div class='news-meta'><span>來源: {source}</span><span>{time_str}</span></div>"
                f"</li>"
            )
        return "".join(html_snippets)
    except Exception as e:
        log_msg(f"❌ 新聞 RSS 解析嚴重錯誤 ({display_name}): {e}")
        return f"<li class='news-item'>新聞加載失敗，請稍後重試。</li>"

def update_html_price_row(content, row_id, change_pct, is_us=True):
    sign = "+" if change_pct >= 0 else ""
    color = "var(--us-up)" if change_pct >= 0 else "var(--us-down)"
    if not is_us:
        color = "var(--tw-up)" if change_pct >= 0 else "var(--tw-down)"
    
    pattern = rf'(<div class="change-row" id="{row_id}">.*?</span><span style=\').*?(\'>.*?</span></div>)'
    replacement = rf"\g<1>color: {color};\g<2>"
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    pattern_val = rf'(<div class="change-row" id="{row_id}"><span>漲跌幅</span><span style=\'color: [^;\']+(?:;)?\'>).*?(</span></div>)'
    replacement_val = rf"\g<1>{sign}{change_pct:.2f}%\g<2>"
    return re.sub(pattern_val, replacement_val, content, flags=re.DOTALL)

def update_html_price_val(content, price_id, price_val, prefix=""):
    pattern = rf'(<div class="price-large" id="{price_id}">).*?(</div>)'
    return re.sub(pattern, rf"\g<1>{prefix}{price_val:.2f}\g<2>", content, flags=re.DOTALL)

def update_html_list(content, list_id, new_li_items):
    pattern = rf'(<ul class="news-list" id="{list_id}">).*?(</ul>)'
    if not re.search(pattern, content, flags=re.DOTALL):
        pattern = rf'(<ul class="res-list-container" id="{list_id}">).*?(</ul>)'
    return re.sub(pattern, rf"\g<1>{new_li_items}\g<2>", content, flags=re.DOTALL)

def main():
    html_path = "index.html"
    if not os.path.exists(html_path):
        log_msg(f"找不到 {html_path} 檔案！")
        return
        
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    log_msg("開始從 Yahoo Finance 同步即時報價數據...")
    vti_p, vti_c = fetch_from_yahoo("VTI", 301.12, 1.45)
    vxus_p, vxus_c = fetch_from_yahoo("VXUS", 63.45, 0.85)
    vt_p, vt_c = fetch_from_yahoo("VT", 121.34, 1.12)
    tw50_p, tw50_c = fetch_from_yahoo("0050.TW", 185.30, 2.15)
    tsmc_p, tsmc_c = fetch_from_yahoo("2330.TW", 935.00, 3.45)
    honhai_p, honhai_c = fetch_from_yahoo("2317.TW", 192.50, -1.02)
    japan_p, japan_c = fetch_from_yahoo("00981A.TW", 15.42, 0.65)
    
    # 1. 更新報價數值與顏色
    content = update_html_price_val(content, "vti_p", vti_p, "$")
    content = update_html_price_val(content, "vxus_p", vxus_p, "$")
    content = update_html_price_val(content, "vt_p", vt_p, "$")
    content = update_html_price_val(content, "0050_p", tw50_p, "$")
    content = update_html_price_val(content, "tsmc_p", tsmc_p, "$")
    content = update_html_price_val(content, "honhai_p", honhai_p, "$")
    content = update_html_price_val(content, "japan_p", japan_p, "$")
    
    content = update_html_price_row(content, "vti_row", vti_c, is_us=True)
    content = update_html_price_row(content, "vxus_row", vxus_c, is_us=True)
    content = update_html_price_row(content, "vt_row", vt_c, is_us=True)
    content = update_html_price_row(content, "0050_row", tw50_c, is_us=False)
    content = update_html_price_row(content, "tsmc_row", tsmc_c, is_us=False)
    content = update_html_price_row(content, "honhai_row", honhai_c, is_us=False)
    content = update_html_price_row(content, "japan_row", japan_c, is_us=False)
    
    # 2. 個股新聞同步
    content = update_html_list(content, "news_VTI", fetch_stock_all_news("VTI", "VTI ETF"))
    content = update_html_list(content, "news_VXUS", fetch_stock_all_news("VXUS", "VXUS ETF"))
    content = update_html_list(content, "news_VT", fetch_stock_all_news("VT", "VT ETF"))
    content = update_html_list(content, "news_0050", fetch_stock_all_news("0050.TW", "0050"))
    content = update_html_list(content, "news_2330", fetch_stock_all_news("2330.TW", "台積電"))
    content = update_html_list(content, "news_2317", fetch_stock_all_news("2317.TW", "鴻海"))
    content = update_html_list(content, "news_00981A", fetch_stock_all_news("00981A.TW", "00981A"))

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)
    log_msg("🎉 網頁更新任務順利執行完畢！")

if __name__ == "__main__":
    main()
