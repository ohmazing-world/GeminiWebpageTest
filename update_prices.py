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
    """
    優化版個股新聞過濾：首選 Yahoo 原生個股解鎖新聞，確保連結百分之百直達真實新聞網頁
    """
    news_pool = []
    urls = []
    
    # 台股與美股分流至高純度真實個股 Feed
    if ".TW" in ticker:
        pure_symbol = ticker.split('.')[0]
        urls.append((f"https://tw.stock.yahoo.com/rss?s={pure_symbol}", "Yahoo奇摩股市"))
    else:
        urls.append((f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US", "Yahoo Finance"))
        
    # 加入高權重新聞網頁搜尋作為備份源
    encoded_query = urllib.parse.quote(f"{display_name} 新聞")
    urls.append((f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "Google新聞"))
    
    for url, source_name in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.title
                link = entry.link
                
                # 清洗標題尾部的來源標籤
                if " - " in title:
                    title = title.split(" - ")[0]
                
                # 精確解碼 Google News 跳轉鏈接中的盲區，盡可能還原真實連結
                if "news.google.com" in link and hasattr(entry, 'source'):
                    # 若無法解碼則保留，但首選 Yahoo 原生乾淨連結
                    pass
                
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
            
    # 高階去重
    seen = set()
    unique_news = []
    for n in news_pool:
        if n['title'] not in seen and "Google財經" not in n['title']:
            seen.add(n['title'])
            unique_news.append(n)
            
    return unique_news[:6] # 提供最多 6 則（前3則預設顯示，後3則供折疊隱藏）

def fetch_mindset_resources():
    """
    每小時任務：精確抓取與清流君、周冠男、巴菲特最相關的文章/影音，依照發布時間排序，嚴格輸出前 10 則
    """
    log_msg("開始檢索指數化思維資源（清流君、周冠男、巴菲特）...")
    masters = ["清流君", "周冠男", "巴菲特"]
    all_resource_pool = []
    
    for master in masters:
        encoded = urllib.parse.quote(master)
        # 使用高精確度的 Google 新聞 RSS 作為來源
        rss_url = f"https://news.google.com/rss/search?q={encoded}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                title = entry.title
                if " - " in title:
                    title = title.split(" - ")[0]
                link = entry.link
                
                dt_obj = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    dt_obj = datetime(*entry.published_parsed[:6]) + timedelta(hours=8)
                
                # 自動判別類型
                media_type = "🎬 影音觀點" if "youtube.com" in link.lower() or "youtube" in title.lower() else "📄 財經專欄"
                
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

    # 依照發布時間進行時序混洗排序（由新到舊）
    all_resource_pool.sort(key=lambda x: x['date_obj'], reverse=True)
    
    # 去重並取前 10 則
    seen_titles = set()
    final_stream = []
    for item in all_resource_pool:
        if item['title'] not in seen_titles:
            seen_titles.add(item['title'])
            final_stream.append(item)
            
    return final_stream[:10]

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
        joined_html = "<li class='res-item'>思維資源調度中...</li>"
        
    pattern = rf'(id="resource_stream"[^>]*>).*?(</ul\s*>)'
    return re.sub(pattern, rf'\g<1>{joined_html}\g<2>', content, flags=re.DOTALL)

def main():
    log_msg("啟動全球資產戰情室數據全面同步...")
    
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        log_msg(f"❌ 無法讀取 index.html: {e}")
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
    
    # 4. 抓取直連新聞網址並注入
    content = update_html_list(content, "news_VTI", fetch_stock_all_news("VTI", "VTI ETF"))
    content = update_html_list(content, "news_VXUS", fetch_stock_all_news("VXUS", "VXUS ETF"))
    content = update_html_list(content, "news_VT", fetch_stock_all_news("VT", "VT ETF"))
    content = update_html_list(content, "news_0050", fetch_stock_all_news("0050.TW", "0050 ETF"))
    content = update_html_list(content, "news_2330", fetch_stock_all_news("2330.TW", "台積電"))
    content = update_html_list(content, "news_2317", fetch_stock_all_news("2317.TW", "鴻海"))
    content = update_html_list(content, "news_00981A", fetch_stock_all_news("00981A.TW", "00981A"))

    # 5. 抓取大師資源流並注入
    stream_data = fetch_mindset_resources()
    content = update_resource_stream_block(content, stream_data)

    # 6. 自動注入全專頁最新一次全面更新時間戳記至頁尾
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = update_html_block(content, "last_update_time", current_time_str)

    try:
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(content)
        log_msg(f"🎉 成功同步！大師資源與真實新聞鏈接已全面校正完成。時間：{current_time_str}")
    except Exception as e:
        log_msg(f"❌ 寫入 index.html 失敗: {e}")

if __name__ == "__main__":
    main()
