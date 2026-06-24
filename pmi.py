from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import csv
import os


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
# 2. HTML 파싱 함수 (BeautifulSoup)
# =========================
def parse_respondents(html):

    soup = BeautifulSoup(html, "html.parser")

    results = []

    h3 = soup.find(lambda tag:
        tag.name in ["h3", "h2"] and
        tag.get_text(strip=True) and
        "WHAT RESPONDENTS ARE SAYING" in tag.get_text()
    )

    if not h3:
        return results

    current = h3.find_next()

    while current:

        if current.get_text(strip=True) and "MANUFACTURING AT A GLANCE" in current.get_text():
            break

        if current.name == "li":
            results.append(current.get_text(strip=True))

        current = current.find_next()

    return results


# =========================
# 3. 크롤링 함수
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

        print(f"{report_type} {month} 없음 → 지난달 이동:", url)

        page.goto(url)
        page.wait_for_timeout(5000)

        used_month = fallback_month

    # =========================
    # HTML 전체 가져오기
    # =========================
    html = page.content()

    respondents = parse_respondents(html)

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
# 4. 실행
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
    # 5. CSV 저장
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
    # 6. Git push (GitHub Actions)
    # =========================
    os.system("git config --global user.name 'github-actions'")
    os.system("git config --global user.email 'github-actions@github.com'")
    os.system("git add .")
    os.system(f"git commit -m 'Add PMI report {timestamp}'")
    os.system("git push")

    browser.close()
