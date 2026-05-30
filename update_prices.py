import yfinance as yf
from datetime import datetime, timedelta
import sys
import feedparser
import urllib.parse
import re
import base64

def log_msg(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 {msg}")
    sys.stdout.flush()

def decode_google_news_url(source_url):
    """
    精確逆向解碼 Google News RSS 加密連結，提取真正的原始正文 URL，
    防止跳轉被攔截時退回來源網站首頁。
    """
    if "news.google.com" not in source_url:
        return source_url
    try:
        path = source_url.split("articles/")[-1].split("?")[0]
        # 補齊 Base64 填充字元
        padding = len(path) % 4
        if padding != 0:
            path += "=" * (4 - padding)
        
        decoded_bytes = base64.urlsafe_b64decode(path)
        # 嘗試從二進位字串中搜尋包含完整協定的網址
        decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
        
        urls = re.findall(r'https?://[^\s\x00-\x1f\x7f-\xff"\'<>]+', decoded_str)
        if urls:
            # 篩選掉指向 google 自身的無效連結
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

def fetch_stock_all_news(ticker, display_name, fetch_index_news=False):
    """
    個股與指數新聞抓取：
    如果是美股大盤 ETF (VT, VXUS, VTI)，除了代號外，還會額外連動檢索「指數化投資」中文權威新聞。
    """
    news_pool = []
    urls = []
    
    # 1. 抓取 Yahoo 財經原生管道
    if ".TW" in ticker:
        pure_symbol = ticker.split('.')[0]
        urls.append((f"https://tw.stock.yahoo.com/rss?s={pure_symbol}", "Yahoo奇摩股市"))
    else:
        urls.append((f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US", "Yahoo Finance"))
        
    # 2. 抓取 Google 新聞針對代號與名稱的搜尋
    encoded_query = urllib.parse.quote(f"{display_name} 新聞")
    urls.append((f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "Google新聞"))
    
    # 3. 針對美股全市場 ETF 擴充：自動匯入台灣本地「指數化投資」中文即時市況報導
    if fetch_index_news:
        encoded_idx_query = urllib.parse.quote("指數化投資")
        urls.append((f"https://news.google.com/rss/search?q={encoded_idx_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "指數化思維"))

    for url, source_name in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.title
                link = entry.link
                
                if " - " in title:
                    title = title.split(" - ")[0]
                
                # 如果是 Google 新聞來源，進行解碼還原成真實網址
                if "news.google.com" in link:
                    link = decode_google_news_url(link)
                
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
                    "time": pub_time,
                    "is_chinese": not bool(re.search(r'[a-zA-Z]{15,}', title)) # 簡單判定是否主要為中文
                })
        except Exception as e:
            log_msg(f"新聞抓取異常 ({ticker}): {e}")
            
    seen = set()
    unique_news = []
    
    # 為了最佳體驗，如果是有開啟中文擴充的標的，讓中文新聞排在前面，英文排後面
    if fetch_index_news:
        news_pool.sort(key=lambda x: x['is_chinese'], reverse=True)
        
    for n in news_pool:
        if n['title'] not in seen and "Google" not in n['title']:
            seen.add(n['title'])
            unique_news.append(n)
            
    return unique_news[:6]

def fetch_mindset_resources():
    """
    抓取清流君、周冠男、巴菲特的最新文章或影音，整合後按時間由新到舊排序，總數最多 10 則。
    """
    log_msg("檢索大師思維資源（清流君、周冠男、巴菲特）...")
    masters = ["清流君", "周冠男", "巴菲特"]
    all_resource_pool = []
    
    for master in masters:
        encoded = urllib.parse.quote(master)
        rss_url = f"https://news.google.com/rss/search?q={encoded}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                title = entry.title
                if " - " in title:
                    title = title.split(" - ")[0]
                
                link = decode_google_news_url(entry.link)
                
                dt_obj = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    dt_obj = datetime(*entry.published_parsed[:6]) + timedelta(hours=8)
                
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

    # 按發布時間從新到舊進行全局排序
    all_resource_pool.sort(key=lambda x: x['date_obj'], reverse=True)
    
    seen_titles = set()
    final_list = []
    for item in all_resource_pool:
        if item['title'] not in seen_titles:
            seen_titles.add(item['title'])
            final_list.append(item)
            
    return final_list[:10]

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

def inject_split_resources_into_html(content, stream_data):
    """
    將前 10 則數據按人物分流注入對應的 HTML 容器中
    """
    classified = {"清流君": [], "周冠男": [], "巴菲特": []}
    for item in stream_data:
        if item['author'] in classified:
            classified[item['author']].append(item)
            
    for author, items in classified.items():
        html_items = []
        for item in items:
            html_items.append(
                f"<li class='res-item'>"
                f"  <a href='{item['link']}' target='_blank'>{item['title']}</a>"
                f"  <div class='res-tags'>"
                f"    <span class='tag-type'>{item['type']}</span>"
                f"    <span class='tag-time'>{item['time_str']}</span>"
                f"  </div>"
                f"</li>"
            )
        joined_html = "".join(html_items)
        if not joined_html:
            joined_html = "<li class='res-item' style='color: var(--text-sub);'>近期無更新。</li>"
            
        pattern = rf'(id="res_{author}"[^>]*>).*?(</ul\s*>)'
        content = re.sub(pattern, rf'\g<1>{joined_html}\g<2>', content, flags=re.DOTALL)
        
    return content

def main():
    log_msg("啟動全球資產數據與中文指數化投資新聞深度同步...")
    
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        log_msg(f"❌ 無法讀取 index.html: {e}")
        return

    # 1. 股價即時數據同步
    vti_p, vti_c = fetch_from_yahoo("VTI", 372.54, 0.17)
    vxus_p, vxus_c = fetch_from_yahoo("VXUS", 86.06, 0.07)
    vt_p, vt_c = fetch_from_yahoo("VT", 158.12, -0.05)
    
    tw50_p, tw50_c = fetch_from_yahoo("0050.TW", 105.40, 4.82)
    tsmc_p, tsmc_c = fetch_from_yahoo("2330.TW", 2355.0, 3.52)
    honhai_p, honhai_c = fetch_from_yahoo("2317.TW", 289.0, 10.52)
    japan_p, japan_c = fetch_from_yahoo("00981A.TW", 31.54, 2.70)

    # 2. 數據注入卡牌
    content = update_html_block(content, "vti_p", f"${vti_p:.2f}")
    content = update_html_block(content, "vxus_p", f"${vxus_p:.2f}")
    content = update_html_block(content, "vt_p", f"${vt_p:.2f}")
    content = update_html_block(content, "0050_p", f"${tw50_p:.2f}")
    content = update_html_block(content, "tsmc_p", f"${tsmc_p:.1f}")
    content = update_html_block(content, "honhai_p", f"${honhai_p:.1f}")
    content = update_html_block(content, "japan_p", f"${japan_p:.2f}")
    
    content = update_html_price_row(content, "vti_row", vti_c, is_us=True)
    content = update_html_price_row(content, "vxus_row", vxus_c, is_us=True)
    content = update_html_price_row(content, "vt_row", vt_c, is_us=True)
    content = update_html_price_row(content, "0050_row", tw50_c, is_us=False)
    content = update_html_price_row(content, "tsmc_row", tsmc_c, is_us=False)
    content = update_html_price_row(content, "honhai_row", honhai_c, is_us=False)
    content = update_html_price_row(content, "japan_row", japan_c, is_us=False)
    
    # 3. 解析真實連結新聞並注入 (針對美股大盤加入 fetch_index_news=True 以獲取中文指數化投資新聞)
    content = update_html_list(content, "news_VTI", fetch_stock_all_news("VTI", "VTI ETF", fetch_index_news=True))
    content = update_html_list(content, "news_VXUS", fetch_stock_all_news("VXUS", "VXUS ETF", fetch_index_news=True))
    content = update_html_list(content, "news_VT", fetch_stock_all_news("VT", "VT ETF", fetch_index_news=True))
    content = update_html_list(content, "news_0050", fetch_stock_all_news("0050.TW", "0050"))
    content = update_html_list(content, "news_2330", fetch_stock_all_news("2330.TW", "台積電"))
    content = update_html_list(content, "news_2317", fetch_stock_all_news("2317.TW", "鴻海"))
    content = update_html_list(content, "news_00981A", fetch_stock_all_news("00981A.TW", "00981A"))

    # 4. 抓取大師思維流
    stream_data = fetch_mindset_resources()
    content = inject_split_resources_into_html(content, stream_data)

    # 5. 更新時間戳記
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = update_html_block(content, "last_update_time", current_time_str)

    try:
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(content)
        log_msg(f"🎉 修正成功！VTI/VXUS/VT 欄位已成功混入高相關的中文『指數化投資』市況動態。時間：{current_time_str}")
    except Exception as e:
        log_msg(f"❌ 寫入 index.html 失敗: {e}")

if __name__ == "__main__":
    main()
