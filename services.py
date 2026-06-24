from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import json
import os

import gspread
from google.oauth2.service_account import Credentials


# =========================
# 날짜 세팅
# =========================

today = datetime.now()

current_month = today.strftime("%B").lower()

previous_month = (
    today.replace(day=1) - timedelta(days=1)
).strftime("%B").lower()

timestamp = datetime.now().strftime("%Y%m%d_%H%M")


def make_url(month):
    return f"https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/services/{month}/"


# =========================
# 크롤링 시작
# =========================

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )

    page = browser.new_page()


    def scrape(month):

        url = make_url(month)

        print("접속 URL:", url)

        page.goto(url)
        page.wait_for_timeout(5000)

        body = page.locator("body").inner_text()

        used_month = month

        if "no longer available" in body:

            url = make_url(previous_month)

            page.goto(url)
            page.wait_for_timeout(5000)

            used_month = previous_month


        respondents = page.locator("#respondentsSay + ul li").all_inner_texts()

        rows = page.locator("table tbody tr")

        table = []

        for i in range(rows.count()):
            cells = rows.nth(i).locator("th, td").all_inner_texts()
            table.append(cells)

        return used_month, respondents, table


    # =========================
    # SERVICES 실행
    # =========================

    used_month, respondents, table = scrape(current_month)


    # =========================
    # Google Sheets
    # =========================

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

    sheet = client.open("지표").worksheet("ISM DATA")


    # =========================
    # 데이터 구성
    # =========================

    rows = []

    rows.append(["===== SERVICES ====="])
    rows.append(["WHAT RESPONDENTS ARE SAYING"])

    for r in respondents:
        rows.append([r])

    rows.append([])

    for r in table:
        if len(r) < 2:
            continue

        rows.append([
            r[0],
            r[1],
            used_month.capitalize()
        ])


    # =========================
    # 업로드
    # =========================

    sheet.append_rows(rows, value_input_option="RAW")

    print("SERVICES 업로드 완료")

    browser.close()
