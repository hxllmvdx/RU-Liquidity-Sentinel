import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import os

class ReservesParser():
    def __init__(self):
        self.download_path = os.path.join(os.getcwd(), 'data', 'raw')
    
    def parse(self, date_from="01.01.2004", date_to=None):
        if date_to is None:
            date_to = datetime.today().strftime("%d.%m.%Y")
        URL = "https://www.cbr.ru/hd_base/RReserves/"
        headers = {"User-Agent": "Mozilla/5.0"}
        params = {"UniDbQuery.Posted": "True",
            "UniDbQuery.From": date_from,
            "UniDbQuery.To": date_to,
        }
        response = requests.get(URL, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")
        headers_row = [th.get_text(strip=True).replace("\xa0", " ") for th in table.find_all("th")]

        rows = []
        for tr in table.find_all("tr")[1:]:
            cols = tr.find_all("td")
            if cols:
                row = [td.get_text(strip=True).replace("\xa0", " ") for td in cols]
                rows.append(row)
        df = pd.DataFrame(rows, columns=headers_row[:len(rows[0])])
        if "Дата" in df.columns:
            df["Дата"] = pd.to_datetime(df["Дата"], dayfirst=True)
            df = df.sort_values("Дата")
        for col in df.columns[1:]:
            df[col] = (df[col].astype(str).str.replace(" ", "", regex=False).str.replace(",", ".", regex=False))
            df[col] = pd.to_numeric(df[col], errors="coerce")
        output_file = f"cbr_reserves_{date_from.replace('.', '-')}_to_{date_to.replace('.', '-')}.csv"
        file_path = os.path.join(self.download_path, output_file)
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        return 

parser = ReservesParser()
parser.parse()