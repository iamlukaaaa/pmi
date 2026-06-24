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
    return (
        "https://www.ismworld.org/"
        "supply-management-news-and-reports/"
        f"reports/ism-pmi-reports/{report_type}/{month}/"
    )


# =========================
# 2. 크롤링 시작 (예전 안정 구조 복원)
# =========================

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )

    page = browser.new_page()


    # =====================================================
    # SERVICES 스크래핑 (예전 방식 그대로)
    # =====================================================

    def scrape_report(report_type, month):

        url = make_url(report_type, month)

        print("접속 URL:", url)

        page.goto(url)
        page.wait_for_load_state("networkidle")

        body_text = page.locator("body").inner_text()

        used_month = month

        if "The content you are looking for is no longer available." in body_text:

            fallback_month = previous_month

            url = make_url(report_type, fallback_month)

            print(f"{report_type} {month} 없음 → 지난달 이동:", url)

            page.goto(url)
            page.wait_for_timeout(5000)

            used_month = fallback_month


        # =========================
        # RESPONDENTS (예전 방식)
        # =========================

        li_items = page.locator(
            "#respondentsSay + ul li"
        ).all_inner_texts()


        # =========================
        # TABLE (예전 방식)
        # =========================

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
    # 실행 (SERVICES만)
    # =========================

    services_data = scrape_report("services", current_month)

    final_month = services_data["month"]


    # =========================
    # CSV 저장 (예전 구조 유지)
    # =========================

    filename = f"ism_services_{final_month}_{timestamp}.csv"

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:

        writer = csv.writer(f)

        writer.writerow(["===== SERVICES REPORT ====="])
        writer.writerow(["WHAT RESPONDENTS ARE SAYING"])

        for item in services_data["respondents"]:
            writer.writerow([item])

        writer.writerow([])

        writer.writerow([
            "Index",
            "May",
            "Apr",
            "Change",
            "Direction",
            "Rate",
            "Trend"
        ])

        writer.writerows(services_data["table"])


    print(f"\nCSV 저장 완료: {filename}")


    # =========================
    # Google Sheets 업로드 (유지)
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

    sheet = client.open("지표").worksheet("ISM DATA")


    # =========================
    # SHEETS 업로드 (예전 + 유지)
    # =========================

    rows_to_append = []

    rows_to_append.append(["===== SERVICES ====="])
    rows_to_append.append(["WHAT RESPONDENTS ARE SAYING"])

    for item in services_data["respondents"]:
        rows_to_append.append([item])

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

    print("Google Sheets 업데이트 완료")

    browser.close()
