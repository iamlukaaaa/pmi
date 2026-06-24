from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import csv


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

    browser = p.chromium.launch(headless=False)
    page = browser.new_page()


    # =====================================================
    # PMI 먼저 실행 (여기서 기준 month 결정)
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
    # PMI 먼저 실행
    # =========================
    pmi_data = scrape_report("pmi", current_month)

    # ⭐ 핵심: SERVICES는 PMI에서 결정된 월을 그대로 사용
    services_data = scrape_report("services", pmi_data["month"])


    # =========================
    # CSV 저장
    # =========================
    filename = f"ism_reports_{pmi_data['month']}_{timestamp}.csv"

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:

        writer = csv.writer(f)


        # =========================
        # PMI
        # =========================
        writer.writerow(["===== PMI REPORT ====="])
        writer.writerow(["WHAT RESPONDENTS ARE SAYING"])

        for item in pmi_data["respondents"]:
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

        writer.writerows(pmi_data["table"])


        writer.writerow([])
        writer.writerow([])


        # =========================
        # SERVICES
        # =========================
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

    browser.close()