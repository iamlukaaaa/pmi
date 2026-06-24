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
    return f"https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/{report_type}/{month}/"


# =========================
# 2. 크롤링 시작
# =========================
with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )

    page = browser.new_page()


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
    # ⭐ 변경: SERVICES 먼저 실행
    # =========================
    services_data = scrape_report("services", current_month)

    # PMI는 SERVICES 기준 month 사용
    pmi_data = scrape_report("pmi", services_data["month"])


    # =========================
    # CSV 저장
    # =========================
    filename = f"ism_reports_{pmi_data['month']}_{timestamp}.csv"

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:

        writer = csv.writer(f)

        # =========================
        # SERVICES 먼저 출력
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

        writer.writerow([])
        writer.writerow([])

        # =========================
        # PMI 나중 출력
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


    print(f"\nCSV 저장 완료: {filename}")
    
    
    # =========================
    # Google Sheets 업로드
    # =========================
    
    import json
    import gspread
    from google.oauth2.service_account import Credentials
    
    
    # GitHub Secret "google" 가져오기
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
    
    
    # 실제 구글 스프레드시트 이름 입력
    sheet = client.open("ISM PMI DATA").sheet1
    
    
    # 방금 만든 CSV 읽기
    with open(filename, "r", encoding="utf-8-sig") as f:
        data = list(csv.reader(f))
    
    
    # 기존 내용 삭제 후 새 데이터 입력
    sheet.clear()
    
    sheet.update(
        "A1",
        data
    )
    
    
    print("Google Sheets 업데이트 완료")


    # =========================
    # Git push
    # =========================
    os.system("git config --global user.name 'github-actions'")
    os.system("git config --global user.email 'github-actions@github.com'")
    
    os.system("git add .")
    os.system(f"git commit -m 'Add PMI report {timestamp}'")
    os.system("git push")

    browser.close()
