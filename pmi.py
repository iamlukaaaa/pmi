from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import csv
import os


today = datetime.now()

current_month = today.strftime("%B").lower()

previous_month = (
    today.replace(day=1) - timedelta(days=1)
).strftime("%B").lower()

timestamp = datetime.now().strftime("%Y%m%d_%H%M")


def make_url(report_type, month):
    return f"https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/{report_type}/{month}/"


with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )

    page = browser.new_page()


    def scrape_report(report_type, month):

        url = make_url(report_type, month)

        print("접속 URL:", url)

        page.goto(url, wait_until="networkidle")

        body_text = page.locator("body").inner_text()

        used_month = month

        if "The content you are looking for is no longer available." in body_text:

            fallback_month = previous_month
            url = make_url(report_type, fallback_month)

            print(f"{report_type} {month} 없음 → 지난달 이동:", url)

            page.goto(url, wait_until="networkidle")

            used_month = fallback_month

        # =========================
        # ⭐ 핵심 수정 (PMI 안정화)
        # =========================
        page.wait_for_selector("#respondentsSay + ul li")

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


    # PMI
    pmi_data = scrape_report("pmi", current_month)

    # SERVICES
    services_data = scrape_report("services", pmi_data["month"])


    filename = f"ism_reports_{pmi_data['month']}_{timestamp}.csv"

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:

        writer = csv.writer(f)

        writer.writerow(["===== PMI REPORT ====="])
        writer.writerow(["WHAT RESPONDENTS ARE SAYING"])

        for item in pmi_data["respondents"]:
            writer.writerow([item])

        writer.writerow([])

        writer.writerow([
            "Index", "May", "Apr", "Change", "Direction", "Rate", "Trend"
        ])

        writer.writerows(pmi_data["table"])

        writer.writerow([])
        writer.writerow([])

        writer.writerow(["===== SERVICES REPORT ====="])
        writer.writerow(["WHAT RESPONDENTS ARE SAYING"])

        for item in services_data["respondents"]:
            writer.writerow([item])

        writer.writerow([])

        writer.writerow([
            "Index", "May", "Apr", "Change", "Direction", "Rate", "Trend"
        ])

        writer.writerows(services_data["table"])


    print(f"\nCSV 저장 완료: {filename}")

    os.system("git config --global user.name 'github-actions'")
    os.system("git config --global user.email 'github-actions@github.com'")

    os.system("git add .")
    os.system(f"git commit -m 'Add PMI report {timestamp}'")
    os.system("git push")

    browser.close()
