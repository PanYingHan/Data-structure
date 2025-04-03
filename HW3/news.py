from playwright.sync_api import sync_playwright

def play_youtube_news_live_with_chrome():
    with sync_playwright() as p:
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        user_data_dir = "/tmp/playwright-chrome-profile"

        print("🚀 啟動 Google Chrome 瀏覽器...")
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            executable_path=chrome_path,
        )
        page = browser.pages[0]

        print("📺 前往 YouTube 搜尋頁面...")
        page.goto("https://www.youtube.com/results?search_query=新聞直播", timeout=0)
        page.wait_for_timeout(3000)

        # ✅ 嘗試點掉 cookie 彈窗（如有）
        try:
            cookie_btn = page.locator("button:has-text('接受所有')")
            if cookie_btn.is_visible():
                cookie_btn.click()
                print("🍪 已接受 cookie")
        except:
            pass

        print("⏳ 等待搜尋結果區塊出現...")
        try:
            page.wait_for_selector("ytd-video-renderer", timeout=15000)
        except:
            print("❌ 影片區塊載入失敗，請確認是否卡在登入或地區彈窗")
            input("🔍 手動觀察畫面，按 Enter 關閉瀏覽器...")
            browser.close()
            return

        print("▶️ 點擊第一個可播放影片...")
        videos = page.locator("ytd-video-renderer")

        for i in range(videos.count()):
            try:
                href = videos.nth(i).locator("a#thumbnail").get_attribute("href")
                if href and "/watch?" in href:
                    full_url = f"https://www.youtube.com{href}"
                    page.goto(full_url)
                    print(f"🎬 已前往第 {i+1} 個影片：{full_url}")
                    break
            except:
                continue

        input("📎 播放中，按 Enter 關閉瀏覽器...")
        browser.close()

if __name__ == "__main__":
    play_youtube_news_live_with_chrome()
