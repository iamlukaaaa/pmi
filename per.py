from playwright.sync_api import sync_playwright
from datetime import datetime
import os
import json

import gspread
from google.oauth2.service_account import Credentials


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

        page.goto(URL, timeout=60000)
        page.wait_for_selector("table", timeout=60000)
        page.wait_for_timeout(5000)


        # =========================
        # 날짜
        # =========================
        card = page.locator("div:has(h3:text('Other Indexes'))").first

        timestamp = card.locator(
            "span.WSJBase--card__timestamp--3F2HxyAE"
        ).first.inner_text()

        date_obj = datetime.strptime(
            timestamp,
            "%A, %B %d, %Y"
        )

        formatted_date = f"{date_obj.year}. {date_obj.month}. {date_obj.day}"


        # =========================
        # PER
        # =========================
        rows = page.locator("table tbody tr")

        per_value = None

        for i in range(rows.count()):

            cells = rows.nth(i).locator("td").all_inner_texts()

            if len(cells) >= 4 and "S&P 500 Index" in cells[0]:
                per_value = cells[3]
                break

        browser.close()

        return formatted_date, per_value



# =========================
# Google Sheets 업로드
# =========================
def upload_to_sheets(date, per):

    creds_json = json.loads(os.environ["google"])

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        creds_json,
        scopes=scope
    )

    client = gspread.authorize(creds)

    sheet = client.open("지표").worksheet("PER DATA")

    sheet.append_row(
        [date, per],
        value_input_option="RAW"
    )

    print("Google Sheets 저장 완료")


# =========================
# main
# =========================
if __name__ == "__main__":

    date, per = scrape()

    print("DATE:", date)
    print("PER:", per)

    upload_to_sheets(date, per)
