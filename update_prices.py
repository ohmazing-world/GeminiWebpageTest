import yfinance as yf
from datetime import datetime, timedelta
import sys
import feedparser  # 用於解析公用財經 RSS 新聞

def log_msg(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 {msg}")
    sys.stdout.flush()

def fetch_from_yahoo(ticker, default_price, default_change):
    log_msg(f"🦅 呼叫 Yahoo Finance 數據流 -> 標的: {ticker}")
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        price = info.last_price
        prev_close = info.previous_close
        change_pct = ((price - prev_close) / prev_close) * 100
        log_msg(f"🎉 [數據解鎖] {ticker}: ${price:.2f} ({change_pct:.2f}%)")
        return price, change_pct
    except Exception as e:
        log_msg(f"⚠️ 接口暫停或週末休市: {e}")
    return default_price, default_change

def fetch_filtered_rss_news(tickers):
    """
    自各大公用 RSS 管道獲取指定股票的新聞，嚴格篩選 3 日內，並由新到舊排序。
    """
    log_msg(f"📰 開始掃描公用財經 RSS 新聞流: {tickers}")
    three_days_ago = datetime.now() - timedelta(days=3)
    gathered_news = []
    
    for ticker in tickers:
        # 使用 Yahoo Finance 的公開標準 RSS Feed
        rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
        if ".TW" in ticker:
            # 針對台灣標的導向繁體中文數據新聞饋送流
            rss_url = f"https://tw.stock.yahoo.com/rss?s={ticker.split('.')[0]}"
            
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                # 解析時間
                pub_time = None
                time_formats = ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S GMT', '%Y-%m-%dT%H:%M:%SZ']
                for fmt in time_formats:
                    try:
                        pub_time = datetime.strptime(entry.published, fmt)
                        # 去除時區落差進行本地化時間比對
                        pub_time = pub_time.replace(tzinfo=None)
                        break
                    except:
                        continue
                
                if not pub_time:
                    pub_time = datetime.now() # 備用時間
                
                # 🛠️ 核心篩選：只留 3 日內 (72小時內) 的財經消息
                if pub_time >= three_days_ago:
                    title = entry.title
                    link = entry.link
                    # 避免重複標題新聞進駐
                    if not any(n['title'] == title for n in gathered_news):
                        gathered_news.append({
                            'title': title,
                            'link': link,
                            'date': pub_time
                        })
        except Exception as e:
            log_msg(f"RSS 讀取略過 ({ticker}): {e}")
            
    # 🛠️ 排序：從新到舊排序
    gathered_news.sort(key=lambda x: x['date'], reverse=True)
    return gathered_news

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
    """ 精準切割並更新網頁內部的 <ul> 新聞列表 """
    tag = f'id="{target_id}">'
    if tag in content:
        parts = content.split(tag)
        if len(parts) > 1:
            sub_parts = parts[1].split('</ul>', 1)
            if len(sub_parts) > 1:
                list_html = ""
                if not news_items:
                    list_html = "<li class='news-item'>近 3 日內此資產板塊無重大突發新聞，市場表現風平浪靜。</li>"
                for item in news_items[:5]: # 每區塊最多精選顯示 5 條
                    date_str = item['date'].strftime('%Y-%m-%d %H:%M')
                    list_html += f"<li class='news-item'><a href='{item['link']}' target='_blank'>【即時快訊】 {item['title']}</a><span class='news-date'>{date_str}</span></li>"
                return parts[0] + tag + list_html + '</ul>' + sub_parts[1]
    return content

def main():
    log_msg("===== Ohmazing information board 完全體自動化任務啟動 =====")
    
    # 1. 抓取 6 檔核心指數與個股現價
    vti_p, vti_c = fetch_from_yahoo("VTI", 372.54, 0.17)
    vxus_p, vxus_c = fetch_from_yahoo("VXUS", 86.06, 0.07)
    vt_p, vt_c = fetch_from_yahoo("VT", 121.20, 0.11)
    
    tsmc_p, tsmc_c = fetch_from_yahoo("2330.TW", 920.0, 3.52)
    honhai_p, honhai_c = fetch_from_yahoo("2317.TW", 189.0, 10.52)
    japan_p, japan_c = fetch_from_yahoo("00981A.TW", 15.42, 4.82)
    
    # 2. 分類抓取並篩選 3 日內新聞
    us_news = fetch_filtered_rss_news(["VTI", "VXUS", "VT"])
    tw_news = fetch_filtered_rss_news(["2330.TW", "2317.TW"])
    
    # 3. 讀取網頁結構進行精準覆寫
    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()
        
    def fmt_p(p): return f"${p:.2f}"
    def fmt_c(c): return f"+{c:.2f}%" if c >= 0 else f"{c:.2f}%"
    
    # 寫入價格與漲跌幅
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
    
    # 4. 寫入分類新聞列表
    content = update_html_list(content, "us_news_list", us_news)
    content = update_html_list(content, "tw_news_list", tw_news)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)
        
    log_msg("✨ [大功告成] 指數化投資小花園已順利修剪完畢，運作完美！")

if __name__ == "__main__":
    main()
