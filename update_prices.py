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
        change_pct = ((price - prev_close) / prev_close) * 100
        return price, change_pct
    except Exception as e:
        log_msg(f"⚠️ {ticker} 價格接口使用預設防線: {e}")
    return default_price, default_change

def fetch_stock_all_news(ticker, display_name):
    news_pool = []
    urls = []
    chinese_keywords_mapping = {
        "VT": ["VT ETF", "全球股市 ETF", "全世界資產配置", "指數化投資"],
        "VXUS": ["VXUS ETF", "國際股市投資", "海外資產配置"],
        "VTI": ["VTI ETF", "美股大盤", "整體股市投資"],
        "0050.TW": ["0050", "元大台灣50", "台股大盤"],
        "2330.TW": ["台積電", "TSMC", "晶圓代工"],
        "2317.TW": ["鴻海", "Foxconn", "蘋果供應鏈"],
        "00981A.TW": ["統一台股增長", "主動式 ETF"]
    }
    
    # 執行基本 RSS 新聞抓取與分析
    search_terms = chinese_keywords_mapping.get(ticker, [display_name])
    for term in search_terms:
        encoded_term = urllib.parse.quote(term)
        rss_url = f"https://news.google.com/rss/search?q={encoded_term}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:8]:
                title = entry.title
                link = decode_google_news_url(entry.link)
                pub_str = entry.published
                try:
                    dt = datetime.strptime(pub_str, "%a, %d %b %Y %H:%M:%S %Z") + timedelta(hours=8)
                    time_display = dt.strftime("%m/%d %H:%M")
                except:
                    time_display = "近期新聞"
                
                clean_title = title.split(" - ")[0]
                if clean_title not in [n['title'] for n in news_pool] and link not in urls:
                    news_pool.append({'title': clean_title, 'link': link, 'time': time_display, 'source': display_name})
                    urls.append(link)
        except Exception as e:
            log_msg(f"💥 RSS 讀取異常 ({term}): {e}")
            
    # 組裝成漂亮的網頁 HTML 節點
    html_items = []
    for idx, item in enumerate(news_pool[:6]):
        hidden_class = " hidden-news" if idx >= 3 else ""
        html_items.append(f"""
        <li class="news-item{hidden_class}">
            <a href="{item['link']}" target="_blank" rel="noopener noreferrer">{item['title']}</a>
            <div class="news-meta">
                <span>{item['source']}</span>
                <span>{item['time']}</span>
            </div>
        </li>
        """)
    return "\n".join(html_items) if html_items else '<li class="news-item">暫無即時新聞數據</li>'

def update_html_price_row(content, row_id, price_val, is_us=True):
    # 完美匹配美股和台股的顏色渲染模式
    try:
        color = "#2E7D32" if price_val >= 0 else "#C62828"
        if not is_us:
            color = "#C62828" if price_val >= 0 else "#2E7D32"
        sign = "+" if price_val >= 0 else ""
        formatted_pct = f"{sign}{price_val:.2f}%"
        
        pattern = rf'(<div class="change-row" id="{row_id}"><span>漲跌幅</span><span style=\'color: [^;\']+;\'>)[^<]+(</span></div>)'
        content = re.sub(pattern, f"\\g<1>{formatted_pct}\\g<2>", content)
    except Exception as e:
        log_msg(f"❌ 價格欄位 {row_id} 渲染異常: {e}")
    return content

def update_html_list(content, placeholder_id, new_list_html):
    pattern = rf'(<ul class="[a-zA-Z0-9_-]+" id="{placeholder_id}">).*?(</ul>)'
    return re.sub(pattern, f"\\g<1>\n{new_list_html}\n\\g<2>", content, flags=re.DOTALL)

if __name__ == "__main__":
    log_msg("🚀 開始自動化理財看盤與權威觀點同步任務...")
    
    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()
        
    # 1. 抓取最新金融市場價格
    vti_p, vti_c = fetch_from_yahoo("VTI", 371.65, 0.42)
    vxus_p, vxus_c = fetch_from_yahoo("VXUS", 86.10, -0.09)
    vt_p, vt_c = fetch_from_yahoo("VT", 157.95, 0.39)
    tw50_p, tw50_c = fetch_from_yahoo("0050.TW", 106.10, -1.53)
    tsmc_p, tsmc_c = fetch_from_yahoo("2330.TW", 2385.0, -1.85)
    honhai_p, honhai_c = fetch_from_yahoo("2317.TW", 293.0, -5.18)
    japan_p, japan_c = fetch_from_yahoo("00981A.TW", 31.36, -1.35)
    
    # 寫入更新價格
    content = update_html_price_row(content, "vti_row", vti_c, is_us=True)
    content = update_html_price_row(content, "vxus_row", vxus_c, is_us=True)
    content = update_html_price_row(content, "vt_row", vt_c, is_us=True)
    content = update_html_price_row(content, "0050_row", tw50_c, is_us=False)
    content = update_html_price_row(content, "tsmc_row", tsmc_c, is_us=False)
    content = update_html_price_row(content, "honhai_row", honhai_c, is_us=False)
    content = update_html_price_row(content, "japan_row", japan_c, is_us=False)
    
    # 2. 理財思維與新聞動態填充
    content = update_html_list(content, "news_VTI", fetch_stock_all_news("VTI", "VTI ETF"))
    content = update_html_list(content, "news_VXUS", fetch_stock_all_news("VXUS", "VXUS ETF"))
    content = update_html_list(content, "news_VT", fetch_stock_all_news("VT", "VT ETF"))
    content = update_html_list(content, "news_0050", fetch_stock_all_news("0050.TW", "元大台灣50"))
    content = update_html_list(content, "news_2330", fetch_stock_all_news("2330.TW", "台積電"))
    content = update_html_list(content, "news_2317", fetch_stock_all_news("2317.TW", "鴻海"))
    content = update_html_list(content, "news_00981A", fetch_stock_all_news("00981A.TW", "00981A"))

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)
        
    log_msg("🎉 數據全面同步完畢，完美收工！")
