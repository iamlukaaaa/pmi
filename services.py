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



def make_url(month):

    return (
        "https://www.ismworld.org/"
        "supply-management-news-and-reports/"
        f"reports/ism-pmi-reports/services/{month}/"
    )



# =========================
# 2. 크롤링 시작
# =========================

with sync_playwright() as p:


    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage"
        ]
    )


    page = browser.new_page()



    # =========================
    # SERVICES 스크래핑
    # =========================

    url = make_url(current_month)

    print("접속 URL:", url)


    page.goto(url)

    page.wait_for_timeout(5000)



    body_text = page.locator("body").inner_text()


    used_month = current_month



    # 현재 월 없으면 지난달

    if "The content you are looking for is no longer available." in body_text:


        url = make_url(previous_month)

        print(
            f"services {current_month} 없음 → 지난달 이동:",
            url
        )


        page.goto(url)

        page.wait_for_timeout(5000)


        used_month = previous_month



    # =========================
    # Respondents
    # =========================

    li_items = page.locator(
        "#respondentsSay + ul li"
    ).all_inner_texts()



    # =========================
    # Table
    # =========================

    rows = page.locator(
        "table.table-bordered.table-hover.table-responsive.mb-4 tbody tr"
    )


    table_data = []


    for i in range(rows.count()):

        cells = rows.nth(i).locator(
            "th, td"
        ).all_inner_texts()


        table_data.append(cells)



    # =========================
    # CSV 저장
    # =========================

    filename = (
        f"ism_services_{used_month}_{timestamp}.csv"
    )


    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:


        writer = csv.writer(f)



        writer.writerow(
            ["===== SERVICES REPORT ====="]
        )


        writer.writerow(
            ["WHAT RESPONDENTS ARE SAYING"]
        )


        for item in li_items:

            writer.writerow([item])



        writer.writerow([])



        writer.writerow(
            [
                "Index",
                "May",
                "Apr",
                "Change",
                "Direction",
                "Rate",
                "Trend"
            ]
        )



        writer.writerows(table_data)



    print(
        f"\nCSV 저장 완료: {filename}"
    )



    # =========================
    # Google Sheets 업로드
    # =========================


    creds_json = json.loads(
        os.environ["google"]
    )


    scope = [

        "https://www.googleapis.com/auth/spreadsheets",

        "https://www.googleapis.com/auth/drive"

    ]



    creds = Credentials.from_service_account_info(

        creds_json,

        scopes=scope

    )



    client = gspread.authorize(creds)



    # 실제 시트 이름으로 변경

    sheet = client.open(
        "ISM PMI DATA"
    ).sheet1



    with open(
        filename,
        "r",
        encoding="utf-8-sig"
    ) as f:


        data = list(
            csv.reader(f)
        )



    sheet.clear()



    sheet.update(
        "A1",
        data
    )



    print(
        "Google Sheets 업데이트 완료"
    )



    browser.close()
