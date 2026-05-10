import pandas as pd
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from pathlib import Path
import os

class TaxCalendarParser:
    def __init__(self, xml_path: str = None, xml_string: str = None):
        self.xml_path = xml_path
        self.xml_string = xml_string

    def _get_root(self):
        if self.xml_path:
            raw_text = None
            for enc in ('utf-8', 'windows-1251', 'cp1252', 'latin-1'):
                try:
                    with open(self.xml_path, 'r', encoding=enc) as f:
                        raw_text = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            if raw_text is None:
                raise ValueError(f"Не удалось прочитать {self.xml_path}")
        else:
            raw_text = self.xml_string

        end_tag = '</calendar>'
        pos = raw_text.find(end_tag)
        if pos != -1:
            clean_text = raw_text[:pos + len(end_tag)]
        else:
            clean_text = raw_text
        return ET.fromstring(clean_text)

    @staticmethod
    def _fix_encoding(text: str) -> str:
        if not text or not text.strip():
            return text
        attempts = [
            ('latin-1', 'windows-1251'),
            ('cp1252', 'cp1251'),
        ]
        for wrong_enc, correct_enc in attempts:
            try:
                fixed = text.encode(wrong_enc).decode(correct_enc)
                if any('А' <= ch <= 'я' or ch in 'Ёё' for ch in fixed):
                    return fixed
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
        return text

    @staticmethod
    def _clean_html(html_content: str) -> str:
        if not html_content or not html_content.strip():
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        for a in soup.find_all('a'):
            a.unwrap()
        text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    def parse(self) -> pd.DataFrame:
        root = self._get_root()
        rows = []
        for year_elem in root.findall('year'):
            year = int(year_elem.get('index'))
            for month_elem in year_elem.findall('month'):
                month_name = month_elem.get('name')
                month = pd.Timestamp(f'1 {month_name} {year}').month
                for day_elem in month_elem.findall('day'):
                    day = int(day_elem.get('num'))
                    day_type = day_elem.get('type')
                    date = pd.Timestamp(year=year, month=month, day=day)

                    raw_html = ''.join(day_elem.itertext()).strip()
                    if day_type == 'event':
                        raw_html = self._fix_encoding(raw_html)
                    events_text = self._clean_html(raw_html) if day_type == 'event' else ""

                    rows.append({
                        'date': date,
                        'day_type': day_type,
                        'events_text': events_text
                    })
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values('date').reset_index(drop=True)
        return df


def save_calendar_to_csv(df: pd.DataFrame, output_path: str):
    out = df[['date', 'day_type', 'events_text']].copy()
    out.columns = ['Дата', 'Тип дня', 'Налоговые обязанности']
    out['Налоговые обязанности'] = out['Налоговые обязанности'].str.strip()

    file_exists = os.path.isfile(output_path)
    out.to_csv(
        output_path,
        sep=';',
        index=False,
        encoding='utf-8-sig',
        mode='a' if file_exists else 'w',
        header=not file_exists
    )

folder = Path('data/raw')
xml_files = list(folder.glob('*.xml'))
output_csv = 'data/raw/tax_calendar_all.csv'
if os.path.exists(output_csv):
    os.remove(output_csv)

for xml_file in xml_files:
    parser = TaxCalendarParser(xml_path=str(xml_file))
    df = parser.parse()
    if not df.empty:
        save_calendar_to_csv(df, output_csv)
