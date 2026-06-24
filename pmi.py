from playwright.sync_api import sync_playwright
from datetime import datetime
import csv
import os


# =========================
# 날짜
# =========================
today = datetime.now()
current_month = today.strftime("%B").lower()
timestamp = datetime.now().strftime("%Y%m%d_%H%M")


def make_url(month):
    return f"https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/services/{month}/"


# =========================
# 실행
# =========================
with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )

    page = browser.new_page()

    url = make_url(current_month)
    print("접속 URL:", url)

    page.goto(url)
    page.wait_for_timeout(5000)

    body_text = page.locator("body").inner_text()

    used_month = current_month

    # fallback (없으면 지난달)
    if "The content you are looking for is no longer available." in body_text:
        from datetime import timedelta

        previous_month = (
            datetime.now().replace(day=1) - timedelta(days=1)
        ).strftime("%B").lower()

        url = make_url(previous_month)
        print("현재 월 없음 → 지난달 이동:", url)

        page.goto(url)
        page.wait_for_timeout(5000)

        used_month = previous_month

    # =========================
    # respondents (Services 전용)
    # =========================
    respondents = page.locator(
        "#respondentsSay + ul li"
    ).all_inner_texts()

    # =========================
    # table
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
    filename = f"ism_services_{used_month}_{timestamp}.csv"

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:

        writer = csv.writer(f)

        writer.writerow(["===== SERVICES REPORT ====="])
        writer.writerow(["WHAT RESPONDENTS ARE SAYING"])

        for item in respondents:
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

        writer.writerows(table_data)

    print(f"\nCSV 저장 완료: {filename}")

    # Git push
    os.system("git config --global user.name 'github-actions'")
    os.system("git config --global user.email 'github-actions@github.com'")
    os.system("git add .")
    os.system(f"git commit -m 'Add Services report {timestamp}'")
    os.system("git push")

    browser.close()
