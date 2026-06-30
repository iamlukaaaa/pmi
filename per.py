from playwright.sync_api import sync_playwright
from datetime import datetime


URL = "https://www.wsj.com/market-data/stocks/peyields?eafs_enabled=false"


def scrape():

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        page = browser.new_page()

        print("페이지 접속 중...")

        # =========================
        # 안정 로딩 (GitHub Actions 대응)
        # =========================
        page.goto(URL, timeout=60000)
        page.wait_for_selector("table", timeout=60000)
        page.wait_for_timeout(5000)


        # =========================
        # 날짜 추출 (Other Indexes 기준)
        # =========================

        card = page.locator("div:has(h3:text('Other Indexes'))").first

        timestamp = card.locator(
            "span.WSJBase--card__timestamp--3F2HxyAE"
        ).first.inner_text()

        print("원본 날짜:", timestamp)

        date_obj = datetime.strptime(
            timestamp,
            "%A, %B %d, %Y"
        )

        formatted_date = f"{date_obj.year}. {date_obj.month}. {date_obj.day}"

        print("변환 날짜:", formatted_date)


        # =========================
        # S&P 500 PER 추출
        # =========================

        rows = page.locator("table tbody tr")

        per_value = None

        for i in range(rows.count()):

            cells = rows.nth(i).locator("td").all_inner_texts()

            if len(cells) >= 4 and "S&P 500 Index" in cells[0]:
                per_value = cells[3]
                break

        print("===================")
        print("S&P 500 PER:", per_value)
        print("===================")

        browser.close()

        return formatted_date, per_value


if __name__ == "__main__":

    date, per = scrape()

    print("FINAL OUTPUT")
    print(date, per)
