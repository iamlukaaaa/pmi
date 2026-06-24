from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import csv
import os


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
# 핵심 안정 크롤러
# =========================
def scrape_report(page, report_type, month):

    url = make_url(report_type, month)

    print("접속 URL:", url)

    page.goto(url)
    page.wait_for_timeout(5000)

    body_text = page.locator("body").inner_text()

    used_month = month

    # fallback (지난달)
    if "The content you are looking for is no longer available." in body_text:
        fallback_month = previous_month

        url = make_url(report_type, fallback_month)

        print(f"{report_type} {month} 없음 → 지난달 이동:", url)

        page.goto(url)
        page.wait_for_timeout(5000)

        used_month = fallback_month

    # =========================
    # RESPONDENTS (핵심 안정 로직)
    # =========================
    respondents = page.locator(
        "text=WHAT RESPONDENTS ARE SAYING"
    ).evaluate("""
    (el) => {
        let results = [];

        // 현재 섹션 이후 모든 element 탐색
        let current = el.nextElementSibling;

        while (current) {

            // 종료 조건
            if (current.innerText &&
                current.innerText.includes("MANUFACTURING AT A GLANCE")) {
                break;
            }

            // li 수집
            let lis = current.querySelectorAll("li");
            if (lis.length > 0) {
                lis.forEach(li => {
                    results.push(li.innerText.trim());
                });
            }

            current = current.nextElementSibling;
        }

        return results;
    }
    """)

    # =========================
    # TABLE
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
        "respondents": respondents,
        "table": table_data
    }


# =========================
# 실행
# =========================
with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )

    page = browser.new_page()

    # PMI
    pmi_data = scrape_report(page, "pmi", current_month)

    # SERVICES (PMI 기준 월 유지)
    services_data = scrape_report(page, "services", pmi_data["month"])


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

    # =========================
    # Git push (GitHub Actions용)
    # =========================
    os.system("git config --global user.name 'github-actions'")
    os.system("git config --global user.email 'github-actions@github.com'")
    os.system("git add .")
    os.system(f"git commit -m 'Add PMI report {timestamp}'")
    os.system("git push")

    browser.close()
