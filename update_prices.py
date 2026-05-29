import yfinance as yf
from datetime import datetime, timedelta
import sys
import feedparser
import urllib.parse

def log_msg(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 {msg}")
    sys.stdout.flush()

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
    """
    同時向 Yahoo Finance 與 Google Finance 發起財經新聞 RSS 請求，
    嚴格過濾 3 日內、進行標題去重、並依時間由新到舊排序。
    """
    log_msg(f"🕵️ 正在為 【{display_name}】 調取 Yahoo + Google 雙源核心新聞...")
    three_days_ago = datetime.now() - timedelta(days=3)
    news_pool = []

    # 1. 建立雙源 RSS URL 清單
    urls = []
    # --- 來源 A: Yahoo Finance ---
    if ".TW" in ticker:
        urls.append((f"https://tw.stock.yahoo.com/rss?s={ticker.split('.')[0]}", "Yahoo財經"))
    else:
        urls.append((f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US", "Yahoo財經"))
        
    # --- 來源 B: Google Finance (透過 Google News 財經主題關鍵字訂閱) ---
    encoded_query = urllib.parse.quote(display_name)
    urls.append((f"https://news.google.com/rss/search?q={encoded_query}+when:3d&hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "Google財經"))

    # 2. 開始解析數據流
    for url, source_name in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                pub_time = None
                # 常見 RSS 時間格式解析
                time_formats = ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S GMT', '%Y-%m-%dT%H:%M:%SZ', '%d %b %Y %H:%M:%S %z']
                for fmt in time_formats:
                    try:
                        pub_time = datetime.strptime(entry.published, fmt).replace(tzinfo=None)
                        break
                    except:
                        continue
                
                if not pub_time:
                    pub_time = datetime.now()

                # 核心防線：過濾 3 日內
                if pub_time >= three_days_ago:
                    title = entry.title
                    # 清理 Google 新聞常見的後綴尾巴
                    if " - " in title and source_name == "Google財經":
                        title = title.split(" - ")[0]

                    link = entry.link
                    # 去重機制
                    if not any(n['title'] == title for n in news_pool):
                        news_pool.append({
                            'title': title,
                            'link': link,
                            'date': pub_time,
                            'source': source_name
                        })
        except Exception as e:
            continue

    # 由新到舊排序
    news_pool.sort(key=lambda x: x['date'], reverse=True)
    return news_pool

def update_html_block(content, target_id, new_text):
    tag = f'id="{target_id}">'
    if tag in content:
        parts = content.split(tag)
        if len(parts) > 1:
            sub_parts = parts[1].split('</div>', 1)
            if len(sub_parts) > 1:
                return parts[0] + tag + new_text + '</div>' + sub_parts[1]
    return content

def update_html_list(content, target_id, news_items):
    tag = f'id="{target_id}">'
    if tag in content:
        parts = content.split(tag)
        if len(parts) > 1:
            sub_parts = parts[1].split('</ul>', 1)
            if len(sub_parts) > 1:
                list_html = ""
                if not news_items:
                    list_html = "<li class='news-item' style='color:#7A7571;'>近 3 日內此個股無重大新聞，市場表現平穩。</li>"
                for item in news_items[:4]:  # 每檔個股精選前 4 條最即時新聞
                    date_str = item['date'].strftime('%m-%d %H:%M')
                    list_html += f"<li class='news-item'><a href='{item['link']}' target='_blank'>{item['title']}</a><div class='news-meta'><span>來源: {item['source']}</span><span>{date_str}</span></div></li>"
                return parts[0] + tag + list_html + '</ul>' + sub_parts[1]
    return content

def main():
    log_msg("===== 🚀 核心雙源個股新聞與價格分類對齊同步 =====")
    
    # 價格數據抓取
    vti_p, vti_c = fetch_from_yahoo("VTI", 372.54, 0.17)
    vxus_p, vxus_c = fetch_from_yahoo("VXUS", 86.06, 0.07)
    vt_p, vt_c = fetch_from_yahoo("VT", 121.20, 0.11)
    tsmc_p, tsmc_c = fetch_from_yahoo("2330.TW", 920.0, 3.52)
    honhai_p, honhai_c = fetch_from_yahoo("2317.TW", 189.0, 10.52)
    japan_p, japan_c = fetch_from_yahoo("00981A.TW", 15.42, 4.82)
    
    # 雙源依個股精密新聞歸檔
    vti_news = fetch_stock_all_news("VTI", "VTI")
    vxus_news = fetch_stock_all_news("VXUS", "VXUS")
    vt_news = fetch_stock_all_news("VT", "VT")
    tsmc_news = fetch_stock_all_news("2330.TW", "台積電")
    honhai_news = fetch_stock_all_news("2317.TW", "鴻海")
    japan_news = fetch_stock_all_news("00981A.TW", "00981A")

    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()
        
    fmt_p = lambda p: f"${p:.2f}"
    fmt_c = lambda c: f"+{c:.2f}%" if c >= 0 else f"{c:.2f}%"
    
    # 注入網頁價格
    content = update_html_block(content, "vti_p", fmt_p(vti_p))
    content = update_html_block(content, "vti_c", fmt_c(vti_c))
    content = update_html_block(content, "vxus_p", fmt_p(vxus_p))
    content = update_html_block(content, "vxus_c", fmt_c(vxus_c))
    content = update_html_block(content, "vt_p", fmt_p(vt_p))
    content = update_html_block(content, "vt_c", fmt_c(vt_c))
    content = update_html_block(content, "tsmc_p", f"${tsmc_p:.1f}")
    content = update_html_block(content, "tsmc_c", fmt_c(tsmc_c))
    content = update_html_block(content, "honhai_p", f"${honhai_p:.1f}")
    content = update_html_block(content, "honhai_c", fmt_c(honhai_c))
    content = update_html_block(content, "japan_p", f"${japan_p:.2f}")
    content = update_html_block(content, "japan_c", fmt_c(japan_c))
    
    # 注入個股精密分類新聞
    content = update_html_list(content, "news_VTI", vti_news)
    content = update_html_list(content, "news_VXUS", vxus_news)
    content = update_html_list(content, "news_VT", vt_news)
    content = update_html_list(content, "news_2330", tsmc_news)
    content = update_html_list(content, "news_2317", honhai_news)
    content = update_html_list(content, "news_00981A", japan_news)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)
        
    log_msg("✨ [完全通關] Ohmazing 指數化小花園已全方位升級，外觀與數據極致完美！")

if __name__ == "__main__":
    main()
