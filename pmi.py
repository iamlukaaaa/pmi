from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import csv
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

timestamp = datetime.now().strftime("%Y%m%d_%H%M")


def make_url(report_type, month):
    return f"https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/{report_type}/{month}/"


# =========================
# 2. 크롤링 시작
# =========================

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )

    page = browser.new_page()


    # =========================
    # PMI 스크래핑 함수
    # =========================
    def scrape_report(report_type, month):

        url = make_url(report_type, month)

        print("접속 URL:", url)

        page.goto(url)
        page.wait_for_timeout(5000)

        body_text = page.locator("body").inner_text()

        used_month = month

        if "The content you are looking for is no longer available." in body_text:

            fallback_month = previous_month

            url = make_url(report_type, fallback_month)

            print(f"{report_type} {month} 없음 → 지난달 이동:", url)

            page.goto(url)
            page.wait_for_timeout(5000)

            used_month = fallback_month


        # respondents
        li_items = page.locator("#respondentsSay + ul li").all_inner_texts()


        # table
        rows = page.locator(
            "table.table-bordered.table-hover.table-responsive.mb-4 tbody tr"
        )

        table_data = []

        for i in range(rows.count()):
            cells = rows.nth(i).locator("th, td").all_inner_texts()
            table_data.append(cells)


        return {
            "month": used_month,
            "respondents": li_items,
            "table": table_data
        }


    # =========================
    # PMI 실행
    # =========================

    pmi_data = scrape_report("pmi", current_month)


    # =========================
    # CSV 저장
    # =========================

    filename = f"ism_pmi_{pmi_data['month']}_{timestamp}.csv"

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:

        writer = csv.writer(f)

        writer.writerow(["Index", "Value", "Month"])


        for row in pmi_data["table"]:

            if len(row) < 2:
                continue

            index_name = row[0]
            value = row[1]

            writer.writerow([
                index_name,
                value,
                pmi_data["month"].capitalize()
            ])


    print(f"\nCSV 저장 완료: {filename}")


    # =========================
    # Google Sheets 업로드 (누적 방식)
    # =========================

    print("Google Sheets 업로드 시작")


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


    # 🔥 스프레드시트 이름 (반드시 실제 이름과 동일)
    sheet = client.open("지표").worksheet("ISM DATA")


    rows = []


    for row in pmi_data["table"]:

        if len(row) < 2:
            continue

        index_name = row[0]
        value = row[1]

        rows.append([
            index_name,
            value,
            pmi_data["month"].capitalize()
        ])


    # 🔥 핵심: 누적 저장 (덮어쓰기 아님)
    sheet.append_rows(rows, value_input_option="RAW")


    print("Google Sheets 업데이트 완료")


    browser.close()
