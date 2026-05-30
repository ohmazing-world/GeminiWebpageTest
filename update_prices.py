import yfinance as yf
from datetime import datetime, timedelta
import sys
import feedparser
import urllib.parse
import re

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
    # 修改為容納更多備份新聞，方便 HTML 做前 3 則隱藏機制
    news_pool = []
    urls = []
    
    if ".TW" in ticker:
        urls.append((f"https://tw.stock.yahoo.com/rss?s={ticker.split('.')[0]}", "Yahoo財經"))
    else:
        urls.append((f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US", "Yahoo財經"))
        
    encoded_query = urllib.parse.quote(display_name)
    urls.append((f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "Google財經"))
    
    for url, source_name in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.title
                link = entry.link
                
                # 清洗標題尾端常見的來源贅字
                if " - " in title:
                    title = title.split(" - ")[0]
                    
                pub_time = ""
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    dt = datetime(*entry.published_parsed[:6]) + timedelta(hours=8)
                    pub_time = dt.strftime("%m-%d %H:%M")
                else:
                    pub_time = datetime.now().strftime("%m-%d %H:%M")
                    
                news_pool.append({
                    "title": title,
                    "link": link,
                    "source": source_name,
                    "time": pub_time
                })
        except Exception as e:
            log_msg(f"新聞抓取異常 ({ticker}): {e}")
            
    # 去重
    seen = set()
    unique_news = []
    for n in news_pool:
        if n['title'] not in seen:
            seen.add(n['title'])
            unique_news.append(n)
            
    return unique_news[:6] # 抓取前 6 則供展開使用

def fetch_mindset_resources():
    """
    全新升級：從各大財經 RSS 管道動態搜尋並過濾三位大師的最新文章與影音，
    依照發布時間排序，嚴格輸出前 10 則。
    """
    log_msg("開始檢索指數化思維資源（清流君、周冠男、巴菲特）...")
    masters = ["清流君", "周冠男", "巴菲特"]
    all_resource_pool = []
    
    # 建立搜尋 RSS 核心
    for master in masters:
        encoded = urllib.parse.quote(master)
        rss_url = f"https://news.google.com/rss/search?q={encoded}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                title = entry.title
                if " - " in title:
                    title = title.split(" - ")[0]
                link = entry.link
                
                # 轉換標準時間物件以便精準跨來源排序
                dt_obj = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    dt_obj = datetime(*entry.published_parsed[:6]) + timedelta(hours=8)
                
                # 判定媒體類型
                media_type = "🎬 YouTube影音" if "youtube.com" in link.lower() or "🎬" in title else "📄 財經專欄"
                if "youtube" in title.lower():
                    media_type = "🎬 YouTube影音"
                
                all_resource_pool.append({
                    "title": title,
                    "link": link,
                    "author": master,
                    "type": media_type,
                    "date_obj": dt_obj,
                    "time_str": dt_obj.strftime("%m-%d %H:%M")
                })
        except Exception as e:
            log_msg(f"搜尋大師 {master} 資源時發生異常: {e}")

    # 依時間由新到舊進行混洗排序
    all_resource_pool.sort(key=lambda x: x['date_obj'], reverse=True)
    
    # 去除重複標題
    seen_titles = set()
    final_stream = []
    for item in all_resource_pool:
        if item['title'] not in seen_titles:
            seen_titles.add(item['title'])
            final_stream.append(item)
            
    return final_stream[:10] # 嚴格限制最多 10 則

def update_html_block(content, element_id, new_value):
    pattern = rf'(id="{element_id}"[^>]*>)[^<]*(</)'
    return re.sub(pattern, rf'\g<1>{new_value}\g<2>', content)

def update_html_price_row(content, element_id, change_pct, is_us=True):
    color = "#2E7D32" if change_pct >= 0 else "#C62828"
    if not is_us:
        color = "#C62828" if change_pct >= 0 else "#2E7D32"
    sign = "+" if change_pct >= 0 else ""
    new_html = f"<span>漲跌幅</span><span style='color: {color};'>{sign}{change_pct:.2f}%</span>"
    pattern = rf'(id="{element_id}"[^>]*>).*?(</div\s*>)'
    return re.sub(pattern, rf'\g<1>{new_html}\g<2>', content, flags=re.DOTALL)

def update_html_list(content, element_id, news_list):
    """
    升級版清單注入器：前 3 則為一般項目，第 4 則起自動加上 .hidden-news 類別
    """
    li_html_items = []
    for i, n in enumerate(news_list):
        css_class = "news-item"
        if i >= 3:
            css_class = "news-item hidden-news"
        li_html_items.append(
            f"<li class='{css_class}'><a href='{n['link']}' target='_blank'>{n['title']}</a>"
            f"<div class='news-meta'><span>來源: {n['source']}</span><span>{n['time']}</span></div></li>"
        )
    
    joined_li = "".join(li_html_items)
    if not joined_li:
        joined_li = "<li class='news-item'>暫無即時相關市況新聞。</li>"
        
    pattern = rf'(id="{element_id}"[^>]*>).*?(</ul\s*>)'
    return re.sub(pattern, rf'\g<1>{joined_li}\g<2>', content, flags=re.DOTALL)

def update_resource_stream_block(content, stream_data):
    """
    將排序好的 10 則大師資源流編譯為精美的自適應 HTML 項目並注入網頁
    """
    html_items = []
    for item in stream_data:
        html_items.append(
            f"<li class='res-item'>"
            f"  <a href='{item['link']}' target='_blank'>{item['title']}</a>"
            f"  <div class='res-tags'>"
            f"    <span class='tag-author'>{item['author']}</span>"
            f"    <span class='tag-type'>{item['type']}</span>"
            f"    <span class='tag-time'>{item['time_str']}</span>"
            f"  </div>"
            f"</li>"
        )
    joined_html = "".join(html_items)
    if not joined_html:
        joined_html = "<li class='res-item'>大師指數化思維資源調度中...</li>"
        
    pattern = rf'(id="resource_stream"[^>]*>).*?(</ul\s*>)'
    return re.sub(pattern, rf'\g<1>{joined_html}\g<2>', content, flags=re.DOTALL)

def main():
    log_msg("開始執行每小時全球資產戰情室數據同步任務...")
    
    # 讀取現有網頁
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        log_msg(f"❌ 無法讀取 index.html 基底主檔: {e}")
        return

    # 1. 抓取即時市況數據
    vti_p, vti_c = fetch_from_yahoo("VTI", 372.54, 0.17)
    vxus_p, vxus_c = fetch_from_yahoo("VXUS", 86.06, 0.07)
    vt_p, vt_c = fetch_from_yahoo("VT", 158.12, -0.05)
    
    tw50_p, tw50_c = fetch_from_yahoo("0050.TW", 105.40, 4.82)
    tsmc_p, tsmc_c = fetch_from_yahoo("2330.TW", 2355.0, 3.52)
    honhai_p, honhai_c = fetch_from_yahoo("2317.TW", 289.0, 10.52)
    japan_p, japan_c = fetch_from_yahoo("00981A.TW", 31.54, 2.70)

    # 2. 注入資產現價
    content = update_html_block(content, "vti_p", f"${vti_p:.2f}")
    content = update_html_block(content, "vxus_p", f"${vxus_p:.2f}")
    content = update_html_block(content, "vt_p", f"${vt_p:.2f}")
    content = update_html_block(content, "0050_p", f"${tw50_p:.2f}")
    content = update_html_block(content, "tsmc_p", f"${tsmc_p:.1f}")
    content = update_html_block(content, "honhai_p", f"${honhai_p:.1f}")
    content = update_html_block(content, "japan_p", f"${japan_p:.2f}")
    
    # 3. 注入台美股自適應色彩漲跌幅
    content = update_html_price_row(content, "vti_row", vti_c, is_us=True)
    content = update_html_price_row(content, "vxus_row", vxus_c, is_us=True)
    content = update_html_price_row(content, "vt_row", vt_c, is_us=True)
    content = update_html_price_row(content, "0050_row", tw50_c, is_us=False)
    content = update_html_price_row(content, "tsmc_row", tsmc_c, is_us=False)
    content = update_html_price_row(content, "honhai_row", honhai_c, is_us=False)
    content = update_html_price_row(content, "japan_row", japan_c, is_us=False)
    
    # 4. 抓取並注入限制前 3 則的即時新聞（其餘自動隱藏）
    content = update_html_list(content, "news_VTI", fetch_stock_all_news("VTI", "VTI ETF"))
    content = update_html_list(content, "news_VXUS", fetch_stock_all_news("VXUS", "VXUS ETF"))
    content = update_html_list(content, "news_VT", fetch_stock_all_news("VT", "VT ETF"))
    content = update_html_list(content, "news_0050", fetch_stock_all_news("0050.TW", "元大台灣50"))
    content = update_html_list(content, "news_2330", fetch_stock_all_news("2330.TW", "台積電 2330"))
    content = update_html_list(content, "news_2317", fetch_stock_all_news("2317.TW", "鴻海 2317"))
    content = update_html_list(content, "news_00981A", fetch_stock_all_news("00981A.TW", "00981A"))

    # 5. 抓取大師資源並依發布時間排序注入（最多10則）
    stream_data = fetch_mindset_resources()
    content = update_resource_stream_block(content, stream_data)

    # 6. 自動注入最新一次全面更新時間戳記至頁尾
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = update_html_block(content, "last_update_time", current_time_str)

    # 存檔回寫
    try:
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(content)
        log_msg(f"🎉 任務大成功！所有組件及大師資源已同步完畢。當前時間戳：{current_time_str}")
    except Exception as e:
        log_msg(f"❌ 寫入 index.html 失敗: {e}")

if __name__ == "__main__":
    main()
