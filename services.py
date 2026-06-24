from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import os
import json

import gspread
from google.oauth2.service_account import Credentials


# =========================
# 1. 날짜 세팅
# =========================
today = datetime.now()

current_month = today.strftime("%B").lower()

previous_month = (
    today.replace(day=1) - timedelta(days=1)
).strftime("%B").lower()


def make_url(month):
    return (
        "https://www.ismworld.org/"
        "supply-management-news-and-reports/"
        f"reports/ism-pmi-reports/services/{month}/"
    )


# =========================
# 2. 크롤링
# =========================
with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )

    page = browser.new_page()

    def scrape_report(month):

        url = make_url(month)
        print("접속 URL:", url)

        page.goto(url)
        page.wait_for_timeout(5000)

        body_text = page.locator("body").inner_text()

        used_month = month

        if "The content you are looking for is no longer available." in body_text:
            fallback_month = previous_month

            url = make_url(fallback_month)
            print("fallback →", url)

            page.goto(url)
            page.wait_for_timeout(5000)

            used_month = fallback_month

        respondents = page.locator("#respondentsSay + ul li").all_inner_texts()

        rows = page.locator(
            "table.table-bordered.table-hover.table-responsive.mb-4 tbody tr"
        )

        table_data = []
        for i in range(rows.count()):
            cells = rows.nth(i).locator("th, td").all_inner_texts()
            table_data.append(cells)

        return {
            "month": used_month,
            "respondents": respondents,
            "table": table_data
        }

    # SERVICES 실행
    services_data = scrape_report(current_month)
    final_month = services_data["month"]

    # =========================
    # Google Sheets
    # =========================
    creds_json = json.loads(os.environ["google"])

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(creds_json, scopes=scope)
    client = gspread.authorize(creds)

    sheet = client.open("지표").worksheet("ISM DATA")

    rows_to_append = []

    rows_to_append.append(["===== SERVICES ====="])
    rows_to_append.append(["WHAT RESPONDENTS ARE SAYING"])

    for r in services_data["respondents"]:
        rows_to_append.append([r])

    rows_to_append.append([])

    for row in services_data["table"]:
        if len(row) < 2:
            continue

        rows_to_append.append([
            row[0],
            row[1],
            final_month.capitalize()
        ])

    sheet.append_rows(rows_to_append, value_input_option="RAW")

    print("SERVICES 업로드 완료")

    browser.close()
