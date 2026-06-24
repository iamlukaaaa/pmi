# =========================
# PMI 1 → PMI 2 → SERVICES
# =========================

pmi_data_1 = scrape_report("pmi", current_month)
pmi_data_2 = scrape_report("pmi", current_month)
services_data = scrape_report("services", pmi_data_1["month"])


# =========================
# CSV / SHEETS 출력
# =========================

rows_to_append = []


# =========================
# PMI 1
# =========================
rows_to_append.append(["===== PMI RUN 1 ====="])
rows_to_append.append(["WHAT RESPONDENTS ARE SAYING"])

for r in pmi_data_1["respondents"]:
    rows_to_append.append([r])

rows_to_append.append([])

for row in pmi_data_1["table"]:
    if len(row) < 2:
        continue
    rows_to_append.append([row[0], row[1], pmi_data_1["month"].capitalize()])

rows_to_append.append([])


# =========================
# PMI 2
# =========================
rows_to_append.append(["===== PMI RUN 2 ====="])
rows_to_append.append(["WHAT RESPONDENTS ARE SAYING"])

for r in pmi_data_2["respondents"]:
    rows_to_append.append([r])

rows_to_append.append([])

for row in pmi_data_2["table"]:
    if len(row) < 2:
        continue
    rows_to_append.append([row[0], row[1], pmi_data_2["month"].capitalize()])

rows_to_append.append([])


# =========================
# SERVICES
# =========================
rows_to_append.append(["===== SERVICES ====="])
rows_to_append.append(["WHAT RESPONDENTS ARE SAYING"])

for r in services_data["respondents"]:
    rows_to_append.append([r])

rows_to_append.append([])

for row in services_data["table"]:
    if len(row) < 2:
        continue
    rows_to_append.append([row[0], row[1], services_data["month"].capitalize()])


# =========================
# Google Sheets 업로드
# =========================

sheet.append_rows(rows_to_append, value_input_option="RAW")
