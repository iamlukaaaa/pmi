
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import json
import gspread
from google.oauth2.service_account import Credentials

# =========================
# 1. 날짜
# =========================
today = datetime.now()

current_month = today.strftime("%B").lower()

previous_month = (
    today.replace(day=1) - timedelta(days=1)
).strftime("%B").lower()


# =========================
# 2. URL
# =========================
def make_url(report_type, month):
    return f"https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/{report_type}/{month}/"


# =========================
# 3. 크롤링 함수 (⚠️ 반드시 먼저 선언)
# =========================
def scrape_report(page, report_type, month):

    url = make_url(report_type, month)

    print("접속 URL:", url)

    page.goto(url)
    page.wait_for_timeout(5000)

    body_text = page.locator("body").inner_text()

    used_month = month

    if "The content you are looking for is no longer available." in body_text:

        fallback_month = previous_month

        url = make_url(report_type, fallback_month)

        print(f"{report_type} fallback → {fallback_month}")

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


# =========================
# 4. 실행
# =========================
with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )

    page = browser.new_page()

    # ✅ 이제 정상 호출 가능
    pmi_data_1 = scrape_report(page, "pmi", current_month)
    pmi_data_2 = scrape_report(page, "pmi", current_month)
    services_data = scrape_report(page, "services", pmi_data_1["month"])

    print("PMI1:", len(pmi_data_1["table"]))
    print("PMI2:", len(pmi_data_2["table"]))
    print("SERVICES:", len(services_data["table"]))


    browser.close()
