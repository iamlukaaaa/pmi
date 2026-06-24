from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import csv
import os
import json

import gspread
from google.oauth2.service_account import Credentials


# =========================
    # =====================================================
    # PMI / SERVICES 공통 함수
    # =====================================================
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

        li_items = page.locator("#respondentsSay + ul li").all_inner_texts()

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
    # 실행
    # =========================
    services_data = scrape_report("services", pmi_data["month"])


    # =========================
    # 🔥 핵심 수정: 최종 성공 month 기준
    # =========================
    final_month = services_data["month"]

    # =========================
    # CSV 저장 (복원)
    # =========================

    filename = f"ism_services_{used_month}_{timestamp}.csv"

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:

        writer = csv.writer(f)

        writer.writerow(["===== SERVICES REPORT ====="])
        writer.writerow(["WHAT RESPONDENTS ARE SAYING"])

        for r in respondents:
            writer.writerow([r])

        writer.writerow([])

        writer.writerow(["Index", "Value", "Month"])

        for row in table_data:
            if len(row) < 2:
                continue

            writer.writerow([
                row[0],
                row[1],
                used_month.capitalize()
            ])


    print(f"\nCSV 저장 완료: {filename}")


    # =========================
    # Google Sheets 업로드 (복원)
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
    # SHEETS 데이터 구성 (핵심 복원)
    # =========================

    rows_to_append = []

    # RESPONDENTS
    rows_to_append.append(["===== SERVICES ====="])
    rows_to_append.append(["WHAT RESPONDENTS ARE SAYING"])

    for r in respondents:
        rows_to_append.append([r])

    rows_to_append.append([])

    # TABLE
    for row in table_data:
        if len(row) < 2:
            continue

        rows_to_append.append([
            row[0],
            row[1],
            used_month.capitalize()
        ])


    # =========================
    # 업로드
    # =========================

    sheet.append_rows(rows_to_append, value_input_option="RAW")

    print("Google Sheets 업데이트 완료")

    browser.close()
