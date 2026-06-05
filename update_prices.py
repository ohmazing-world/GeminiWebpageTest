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
        "VXUS": ["VXUS ETF", "國際股市 ETF", "非美股市 配置", "全球資產配置"],
        "VTI": ["VTI ETF", "美股整體市場", "先鋒整體股市", "美股大盤 ETF"]
    }
    
    if ".TW" in ticker:
        pure_symbol = ticker.split('.')[0]
        urls.append((f"https://tw.stock.yahoo.com/rss?s={pure_symbol}", "Yahoo奇摩股市"))
        encoded_query = urllib.parse.quote(f"{display_name} 新聞")
        urls.append((f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "Google新聞"))
    else:
        target_keywords = chinese_keywords_mapping.get(ticker, [f"{ticker} ETF"])
        for kw in target_keywords:
            encoded_kw = urllib.parse.quote(kw)
            urls.append((f"https://news.google.com/rss/search?q={encoded_kw}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "中文財經源"))
        urls.append((f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US", "Yahoo Finance"))

    for url, source_name in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.title
                link = entry.link
                if " - " in title:
                    title = title.split(" - ")[0]
                if "news.google.com" in link:
                    link = decode_google_news_url(link)
                
                dt_obj = get_taiwan_now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    dt_obj = datetime(*entry.published_parsed[:6]) + timedelta(hours=8)
                
                pub_time_str = dt_obj.strftime("%m-%d %H:%M")
                has_chinese = bool(re.search(r'[\u4e00-\u9fff]', title))
                news_pool.append({
                    "title": title, "link": link, "source": source_name,
                    "time": pub_time_str, "date_obj": dt_obj, "has_chinese": has_chinese
                })
        except Exception as e:
            log_msg(f"新聞抓取異常 ({ticker}): {e}")
            
    seen = set()
    unique_news = []
    news_pool.sort(key=lambda x: x['date_obj'], reverse=True)
    news_pool.sort(key=lambda x: x['has_chinese'], reverse=True)
    for n in news_pool:
        if n['title'] not in seen and "Google" not in n['title']:
            seen.add(n['title'])
            unique_news.append(n)
    return unique_news[:8]

def fetch_mindset_resources():
    log_msg("啟動指數化全市場大師思維全網多維度抓取...")
    masters_mapping = {
        "清流君": "清流君", "周冠男": "周冠男", "巴菲特": "巴菲特",
        "約翰伯格": "約翰伯格", "綠角": "綠角", "竹軒": "竹軒", "哆啦王": "哆啦王"
    }
    search_queries = {
        "清流君": "清流君", "周冠男": "周冠男", "巴菲特": "巴菲特",
        "約翰伯格": "約翰·伯格 OR John Bogle", "綠角": "綠角 Greenhorn",
        "竹軒": "竹軒的理財筆記 OR 竹軒 理財", "哆啦王": "哆啦王 ffaarr"
    }
    core_filters = ["etf", "指數", "配置", "美股", "全市場", "複利", "理財", "成本", "內扣", "伯格", "不看盤", "清流", "綠角", "台股", "大盤", "年化", "提領", "本金", "資產"]
    all_resource_pool = []
    
    for key_id, search_term in search_queries.items():
        platform_query = f"({search_term}) (site:facebook.com OR site:threads.net OR site:dcard.tw OR site:news.yahoo.com OR 新聞)"
        encoded_query = urllib.parse.quote(platform_query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                title = entry.title
                if " - " in title: title = title.split(" - ")[0]
                link = decode_google_news_url(entry.link)
                title_lower = title.lower()
                is_highly_relevant = any(token in title_lower for token in core_filters) or (key_id in title)
                if not is_highly_relevant: continue
                
                dt_obj = get_taiwan_now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    dt_obj = datetime(*entry.published_parsed[:6]) + timedelta(hours=8)
                
                if "facebook.com" in link.lower(): media_type = "👥 FB 專頁動態"
                elif "threads.net" in link.lower(): media_type = "🧵 Threads 觀點"
                elif "dcard.tw" in link.lower(): media_type = "💬 Dcard 討論流"
                elif "youtube.com" in link.lower() or "youtube" in title_lower: media_type = "🎬 影音觀點"
                elif "yahoo.com" in link.lower(): media_type = "📰 Yahoo 新聞"
                else: media_type = "📄 財經專欄"
                
                all_resource_pool.append({
                    "title": title, "link": link, "author_key": key_id,
                    "type": media_type, "date_obj": dt_obj,
                    "time_str": dt_obj.strftime("%m-%d %H:%M")
                })
        except Exception as e:
            log_msg(f"搜尋大師 {key_id} 資源時發生異常: {e}")
    all_resource_pool.sort(key=lambda x: x['date_obj'], reverse=True)
    return all_resource_pool

def inject_split_resources_into_html(content, stream_data):
    classified = {"清流君": [], "周冠男": [], "巴菲特": [], "約翰伯格": [], "綠角": [], "竹軒": [], "哆啦王": []}
    for item in stream_data:
        if item['author_key'] in classified: classified[item['author_key']].append(item)
    seen_links = set()
    for author_key, items in classified.items():
        html_items = []
        visible_count = 0
        for item in items:
            if item['link'] in seen_links: continue
            seen_links.add(item['link'])
            css_class = "res-item"
            if visible_count >= 3: css_class = "res-item hidden-res"
            html_items.append(
                f"<li class='{css_class}'>"
                f"  <a href='{item['link']}' target='_blank'>{item['title']}</a>"
                f"  <div class='res-tags'><span class='tag-type'>{item['type']}</span>"
                f"  <span class='tag-time'>{item['time_str']}</span></div>"
                f"</li>"
            )
            visible_count += 1
            if visible_count >= 10: break
        joined_html = "".join(html_items)
        if not joined_html: joined_html = "<li class='res-item' style='color: var(--text-sub);'>近期暫無高度相關思維資產更新。</li>"
        pattern = rf'(id="res_{author_key}"[^>]*>).*?(</ul\s*>)'
        content = re.sub(pattern, rf'\g<1>{joined_html}\g<2>', content, flags=re.DOTALL)
    return content

def update_html_block(content, element_id, new_value):
    pattern = rf'(id="{element_id}"[^>]*>)[^<]*(</)'
    return re.sub(pattern, rf'\g<1>{new_value}\g<2>', content)

def update_html_price_row(content, element_id, change_pct, is_us=True):
    color = "#2E7D32" if change_pct >= 0 else "#C62828"
    if not is_us: color = "#C62828" if change_pct >= 0 else "#2E7D32"
    sign = "+" if change_pct >= 0 else ""
    new_html = f"<span>漲跌幅</span><span style='color: {color};'>{sign}{change_pct:.2f}%</span>"
    pattern = rf'(id="{element_id}"[^>]*>).*?(</div\s*>)'
    return re.sub(pattern, rf'\g<1>{new_html}\g<2>', content, flags=re.DOTALL)

def update_html_list(content, element_id, news_list):
    li_html_items = []
    for i, n in enumerate(news_list):
        css_class = "news-item"
        if i >= 3: css_class = "news-item hidden-news"
        li_html_items.append(
            f"<li class='{css_class}'><a href='{n['link']}' target='_blank'>{n['title']}</a>"
            f"<div class='news-meta'><span>來源: {n['source']}</span><span>{n['time']}</span></div></li>"
        )
    joined_li = "".join(li_html_items)
    if not joined_li: joined_li = "<li class='news-item'>暫無即時相關市況新聞。</li>"
    pattern = rf'(id="{element_id}"[^>]*>).*?(</ul\s*>)'
    return re.sub(pattern, rf'\g<1>{joined_li}\g<2>', content, flags=re.DOTALL)

def ping_google_sitemap():
    """通知 Google 爬蟲 Sitemap 已更新"""
    # 💡 完美同步修正為新的 Repository 名稱 IndexETFGarden
    SITEMAP_URL = "https://ohmazing-world.github.io/IndexETFGarden/sitemap.xml"
    ping_url = f"https://www.google.com/ping?sitemap={SITEMAP_URL}"
    try:
        log_msg(f"正在主動向 Google 提交 Sitemap...")
        resp = requests.get(ping_url, timeout=10)
        if resp.status_code == 200:
            log_msg("✨ Google Sitemap 提交成功！")
        else:
            log_msg(f"⚠️ Google Ping 回傳狀態異常: {resp.status_code}")
    except Exception as e:
        log_msg(f"❌ 無法提交 Sitemap 給 Google: {e}")

def main():
    log_msg("啟動大師陣容全球全管道思維多維度同步...")
    try:
        with open("index.html", "r", encoding="utf-8") as f: content = f.read()
    except Exception as e:
        log_msg(f"❌ 無法讀取 index.html: {e}")
        return

    # 1. 股價同步
    vti_p, vti_c = fetch_from_yahoo("VTI", 372.54, 0.17)
    vxus_p, vxus_c = fetch_from_yahoo("VXUS", 86.06, 0.07)
    vt_p, vt_c = fetch_from_yahoo("VT", 158.12, -0.05)
    tw50_p, tw50_c = fetch_from_yahoo("0050.TW", 105.40, 4.82)
    tsmc_p, tsmc_c = fetch_from_yahoo("2330.TW", 2355.0, 3.52)
    honhai_p, honhai_c = fetch_from_yahoo("2317.TW", 289.0, 10.52)
    japan_p, japan_c = fetch_from_yahoo("00981A.TW", 31.54, 2.70)

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
    
    # 2. 個股新聞同步
    content = update_html_list(content, "news_VTI", fetch_stock_all_news("VTI", "VTI ETF"))
    content = update_html_list(content, "news_VXUS", fetch_stock_all_news("VXUS", "VXUS ETF"))
    content = update_html_list(content, "news_VT", fetch_stock_all_news("VT", "VT ETF"))
    content = update_html_list(content, "news_0050", fetch_stock_all_news("0050.TW", "0050"))
    content = update_html_list(content, "news_2330", fetch_stock_all_news("2330.TW", "台積電"))
    content = update_html_list(content, "news_2317", fetch_stock_all_news("2317.TW", "鴻海"))
    content = update_html_list(content, "news_00981A", fetch_stock_all_news("00981A.TW", "00981A"))

    # 3. 大師思維多維度同步
    stream_data = fetch_mindset_resources()
    content = inject_split_resources_into_html(content, stream_data)

    # 4. 更新時間戳
    taiwan_time_str = get_taiwan_now().strftime("%Y-%m-%d %H:%M")
    content = update_html_block(content, "last_update_time", taiwan_time_str)

    try:
        with open("index.html", "w", encoding="utf-8") as f: f.write(content)
        log_msg(f"🎉 網頁同步完成！")
        ping_google_sitemap()
    except Exception as e:
        log_msg(f"❌ 寫入 index.html 失敗: {e}")

if __name__ == "__main__":
    main()
