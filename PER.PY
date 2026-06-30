from playwright.sync_api import sync_playwright
from datetime import datetime


URL = "https://www.wsj.com/market-data/stocks/peyields?eafs_enabled=false"


with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False   # 테스트라 화면 보이게
    )

    page = browser.new_page()


    print("페이지 접속 중...")
    
    page.goto(
        URL,
        wait_until="networkidle"
    )

    page.wait_for_timeout(5000)


    # =========================
    # 날짜 확인
    # =========================

    timestamp = page.locator(
        "span.WSJBase--card__timestamp--3F2HxyAE"
    ).inner_text()


    print("원본 날짜:", timestamp)


    date_obj = datetime.strptime(
        timestamp,
        "%A, %B %d, %Y"
    )


    formatted_date = (
        f"{date_obj.year}. "
        f"{date_obj.month}. "
        f"{date_obj.day}"
    )


    print("변환 날짜:", formatted_date)



    # =========================
    # 테이블 확인
    # =========================

    rows = page.locator("table tbody tr")


    print("테이블 row 개수:", rows.count())


    for i in range(rows.count()):

        cells = rows.nth(i).locator("td").all_inner_texts()

        print(i, cells)


        if len(cells) >= 4 and "S&P 500 Index" in cells[0]:

            per = cells[3]

            print("===================")
            print("S&P 500 Forward P/E:", per)
            print("===================")

            break


    input("종료하려면 Enter")

    browser.close()
