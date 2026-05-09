from selenium import webdriver
from selenium.webdriver.common.by import By
import os
import urllib.request
class TaxCalendarParser():
    def __init__(self):
        self.download_path = os.path.join(os.getcwd(), 'data', 'raw', 'nalog')
        self.source_name = "nalog_tax_calendar"


    def parse(self):
        driver = webdriver.Chrome()
        url = "https://www.nalog.gov.ru/opendata/7707329152-kalendar/?ysclid=moy272phce597468424"
        driver.get(url)
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            href = link.get_attribute("href")
            if href and (href.endswith(".xml") and ".xml" in href):
                filename = href.split('/')[-1].split('?')[0]
                filepath = os.path.join(self.download_path, filename)
                urllib.request.urlretrieve(href, filepath)
        driver.quit()

parser = TaxCalendarParser()
parser.parse()