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
    three_days_ago = datetime.now() - timedelta(days=3)
    news_pool = []
    urls = []
    
    if ".TW" in ticker:
        urls.append((f"https://tw.stock.yahoo.com/rss?s={ticker.split('.')[0]}", "Yahoo財經"))
    else:
        urls.append((f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US", "Yahoo財經"))
        
    encoded_query = urllib.parse.quote(display_name)
    urls.append((f"https://news.google.com/rss/search?q={encoded_query}+when:3d&hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "Google財經"))

    for url, source_name in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                pub_time = None
                time_formats = ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S GMT', '%Y-%m-%dT%H:%M:%SZ', '%d %b %Y %H:%M:%S %z']
                for fmt in time_formats:
                    try:
                        pub_time = datetime.strptime(entry.published, fmt).replace(tzinfo=None)
                        break
                    except:
                        continue
                if not pub_time:
                    pub_time = datetime.now()

                if pub_time >= three_days_ago:
                    title = entry.title
                    if " - " in title and source_name == "Google財經":
                        title = title.split(" - ")[0]
                    link = entry.link
                    if not any(n['title'] == title for n in news_pool):
                        news_pool.append({
                            'title': title,
                            'link': link,
                            'date': pub_time,
                            'source': source_name
                        })
        except:
            continue
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
                    list_html = "<li class='news-item' style='color:#7A7571;'>近 3 日內無相關個股新聞。</li>"
                for item in news_items[:4]:
                    date_str = item['date'].strftime('%m-%d %H:%M')
                    list_html += f"<li class='news-item'><a href='{item['link']}' target='_blank'>{item['title']}</a><div class='news-meta'><span>來源: {item['source']}</span><span>{date_str}</span></div></li>"
                return parts[0] + tag + list_html + '</ul>' + sub_parts[1]
    return content

def update_html_price_row(content, row_id, change_val, is_us=True):
    tag = f'id="{row_id}">'
    if tag in content:
        parts = content.split(tag)
        if len(parts) > 1:
            sub_parts = parts[1].split('</div>', 1)
            if len(sub_parts) > 1:
                sign = "+" if change_val >= 0 else ""
                if is_us:
                    color = "#2E7D32" if change_val >= 0 else "#C62828"
                else:
                    color = "#C62828" if change_val >= 0 else "#2E7D32"
                    
                new_html = f"<span>漲跌幅</span><span style='color: {color};'>{sign}{change_val:.2f}%</span>"
                return parts[0] + tag + new_html + '</div>' + sub_parts[1]
    return content

def main():
    log_msg("===== 🌳 2026 旗艦配置：Ohmazing board 與 0050 大盤回歸自動化執行 =====")
    
    # 價格數據抓取 (新增 0050.TW 監測線)
    vti_p, vti_c = fetch_from_yahoo("VTI", 372.54, 0.17)
    vxus_p, vxus_c = fetch_from_yahoo("VXUS", 86.06, 0.07)
    vt_p, vt_c = fetch_from_yahoo("VT", 121.20, 0.11)
    tw50_p, tw50_c = fetch_from_yahoo("0050.TW", 185.3, 1.45)
    tsmc_p, tsmc_c = fetch_from_yahoo("2330.TW", 920.0, 3.52)
    honhai_p, honhai_c = fetch_from_yahoo("2317.TW", 189.0, -1.20)
    japan_p, japan_c = fetch_from_yahoo("00981A.TW", 15.42, 1.15)
    
    # 雙源依個股精密新聞歸檔
    vti_news = fetch_stock_all_news("VTI", "VTI")
    vxus_news = fetch_stock_all_news("VXUS", "VXUS")
    vt_news = fetch_stock_all_news("VT", "VT")
    tw50_news = fetch_stock_all_news("0050.TW", "元大台灣50")
    tsmc_news = fetch_stock_all_news("2330.TW", "台積電")
    honhai_news = fetch_stock_all_news("2317.TW", "鴻海")
    japan_news = fetch_stock_all_news("00981A.TW", "統一台股增長主動式ETF")

    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()
        
    # 1. 寫入基本價格
    content = update_html_block(content, "vti_p", f"${vti_p:.2f}")
    content = update_html_block(content, "vxus_p", f"${vxus_p:.2f}")
    content = update_html_block(content, "vt_p", f"${vt_p:.2f}")
    content = update_html_block(content, "0050_p", f"${tw50_p:.2f}")
    content = update_html_block(content, "tsmc_p", f"${tsmc_p:.1f}")
    content = update_html_block(content, "honhai_p", f"${honhai_p:.1f}")
    content = update_html_block(content, "japan_p", f"${japan_p:.2f}")
    
    # 2. 依「美股/台股」慣例，注入客製化漲跌顏色
    content = update_html_price_row(content, "vti_row", vti_c, is_us=True)
    content = update_html_price_row(content, "vxus_row", vxus_c, is_us=True)
    content = update_html_price_row(content, "vt_row", vt_c, is_us=True)
    
    content = update_html_price_row(content, "0050_row", tw50_c, is_us=False)
    content = update_html_price_row(content, "tsmc_row", tsmc_c, is_us=False)
    content = update_html_price_row(content, "honhai_row", honhai_c, is_us=False)
    content = update_html_price_row(content, "japan_row", japan_c, is_us=False)
    
    # 3. 注入個股精密分類新聞
    content = update_html_list(content, "news_VTI", vti_news)
    content = update_html_list(content, "news_VXUS", vxus_news)
    content = update_html_list(content, "news_VT", vt_news)
    content = update_html_list(content, "news_0050", tw50_news)
    content = update_html_list(content, "news_2330", tsmc_news)
    content = update_html_list(content, "news_2317", honhai_news)
    content = update_html_list(content, "news_00981A", japan_news)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)
        
    log_msg("✨ 旗艦大盤完全體更新成功！")

if __name__ == "__main__":
    main()
