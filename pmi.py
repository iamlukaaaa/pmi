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


def make_url(report_type, month):
    return f"https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/{report_type}/{month}/"


# =========================
# 크롤링 함수 (공통)
# =========================

def scrape(page, report_type, month):

    url = make_url(report_type, month)

    print("접속 URL:", url)

    page.goto(url)
    page.wait_for_timeout(5000)

    body = page.locator("body").inner_text()

    used_month = month

    if "no longer available" in body:
        url = make_url(report_type, previous_month)

        print(f"{report_type} {month} 없음 → 이전달 이동")

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
# 실행 시작
# =========================

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )

    page = browser.new_page()


    # =========================
    # PMI
    # =========================

    pmi_month, pmi_resp, pmi_table = scrape(page, "pmi", current_month)


    # =========================
    # SERVICES
    # =========================

    srv_month, srv_resp, srv_table = scrape(page, "services", current_month)


    # =========================
    # Google Sheets 연결
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


    # ===== PMI =====

    rows.append(["===== PMI ====="])
    rows.append(["WHAT RESPONDENTS ARE SAYING"])

    for r in pmi_resp:
        rows.append([r])

    rows.append([])

    for r in pmi_table:
        if len(r) < 2:
            continue

        rows.append([
            r[0],
            r[1],
            pmi_month.capitalize()
        ])


    # ===== SERVICES =====

    rows.append([])
    rows.append(["===== SERVICES ====="])
    rows.append(["WHAT RESPONDENTS ARE SAYING"])

    for r in srv_resp:
        rows.append([r])

    rows.append([])

    for r in srv_table:
        if len(r) < 2:
            continue

        rows.append([
            r[0],
            r[1],
            srv_month.capitalize()
        ])


    # =========================
    # 업로드
    # =========================

    sheet.append_rows(rows, value_input_option="RAW")

    print("PMI + SERVICES 업로드 완료")

    browser.close()
