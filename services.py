from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import os
import json

import gspread
from google.oauth2.service_account import Credentials


# =========================
# 1. URL 생성
# =========================
def make_url(dt):
    month = dt.strftime("%B").lower()
    return (
        "https://www.ismworld.org/"
        "supply-management-news-and-reports/"
        f"reports/ism-pmi-reports/services/{month}/"
    )


def get_previous_month(dt):
    return dt.replace(day=1) - timedelta(days=1)


# =========================
# 2. 크롤링
# =========================
with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )

    page = browser.new_page()

    def scrape_report():

        current_dt = datetime.now().replace(day=1)

        # 1차 시도
        url = make_url(current_dt)
        print("접속 URL:", url)

        page.goto(url)
        page.wait_for_timeout(5000)

        body_text = page.locator("body").inner_text()

        # fallback 처리
        if "The content you are looking for is no longer available." in body_text:
            print("fallback 발생 → 이전 달로 이동")

            current_dt = get_previous_month(current_dt)

            url = make_url(current_dt)
            print("fallback URL:", url)

            page.goto(url)
            page.wait_for_timeout(5000)

        used_month = current_dt.strftime("%B").capitalize()
        used_year = current_dt.year

        respondents = page.locator("#respondentsSay + ul li").all_inner_texts()

        rows = page.locator(
            "table.table-bordered.table-hover.table-responsive.mb-4 tbody tr"
        )

        table_data = []
        for i in range(rows.count()):
            cells = rows.nth(i).locator("th, td").all_inner_texts()
            table_data.append(cells)

        return {
            "year": used_year,
            "month": used_month,
            "respondents": respondents,
            "table": table_data
        }

    # SERVICES 실행
    services_data = scrape_report()

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
            services_data["year"],
            services_data["month"]
        ])

    sheet.append_rows(rows_to_append, value_input_option="RAW")

    print("SERVICES 업로드 완료")

    browser.close()
