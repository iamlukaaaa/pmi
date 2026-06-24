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


# =========================
# URL 생성 (PMI)
# =========================

def make_url(month):
    return (
        "https://www.ismworld.org/"
        "supply-management-news-and-reports/"
        f"reports/ism-pmi-reports/pmi/{month}/"
    )


# =========================
# 2. 크롤링 시작 (예전 방식 복원)
# =========================

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )

    page = browser.new_page()


    # =========================
    # PMI 스크래핑 (예전 안정 방식)
    # =========================

    url = make_url(current_month)

    print("접속 URL:", url)

    page.goto(url)
    page.wait_for_timeout(5000)

    body_text = page.locator("body").inner_text()

    used_month = current_month


    # fallback
    if "The content you are looking for is no longer available." in body_text:

        url = make_url(previous_month)

        print(f"PMI {current_month} 없음 → 지난달 이동:", url)

        page.goto(url)
        page.wait_for_timeout(5000)

        used_month = previous_month


    # =========================
    # RESPONDENTS (예전 방식 그대로)
    # =========================

    respondents = page.locator(
        "#respondentsSay + ul li"
    ).all_inner_texts()


    # =========================
    # TABLE (예전 방식 그대로)
    # =========================

    rows = page.locator(
        "table.table-bordered.table-hover.table-responsive.mb-4 tbody tr"
    )

    table_data = []

    for i in range(rows.count()):
        cells = rows.nth(i).locator("th, td").all_inner_texts()
        table_data.append(cells)


    # =========================
    # CSV 저장
    # =========================

    filename = f"ism_pmi_{used_month}_{timestamp}.csv"

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:

        writer = csv.writer(f)

        writer.writerow(["===== PMI REPORT ====="])
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
    # Google Sheets 업로드
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
    # SHEETS 업로드
    # =========================

    rows_to_append = []

    rows_to_append.append(["===== PMI ====="])
    rows_to_append.append(["WHAT RESPONDENTS ARE SAYING"])

    for r in respondents:
        rows_to_append.append([r])

    rows_to_append.append([])

    for row in table_data:
        if len(row) < 2:
            continue

        rows_to_append.append([
            row[0],
            row[1],
            used_month.capitalize()
        ])


    sheet.append_rows(rows_to_append, value_input_option="RAW")

    print("Google Sheets 업데이트 완료")

    browser.close()
