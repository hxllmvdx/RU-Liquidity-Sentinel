from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os
from datetime import datetime
import time

class RuoniaParser:
    def __init__(self):
        pass
    def parse(self):
        URL = "https://www.cbr.ru/hd_base/ruonia/dynamics/"
        download_dir = os.path.join(os.getcwd(),"data","raw","cbr", "ruonia")
        os.makedirs(download_dir, exist_ok=True)

        options = webdriver.ChromeOptions()

        prefs = {"download.default_directory": download_dir,"download.prompt_for_download": False, "download.directory_upgrade": True}
        options.add_argument("--headless=new")
        options.add_experimental_option("prefs", prefs)
        options.add_argument("--start-maximized")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),options=options)
        wait = WebDriverWait(driver, 30)

        try:
            driver.get(URL)
            time.sleep(2)
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                driver.switch_to.frame(iframes[0])

            table_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,"button.datepicker-filter_button")))
            table_button.click()

            time.sleep(1)

            year_select_element = wait.until(EC.element_to_be_clickable((By.CLASS_NAME,"ui-datepicker-year")))

            year_select_element.click()

            time.sleep(1)

            year_select = Select(year_select_element)
            year_select.select_by_visible_text("2010")

            time.sleep(1)

            month_select_element = wait.until(EC.element_to_be_clickable((By.CLASS_NAME,"ui-datepicker-month")))
            month_select_element.click()

            time.sleep(1)

            month_select = Select(month_select_element)
            month_select.select_by_visible_text("Январь")

            time.sleep(1)

            day_element = wait.until(EC.element_to_be_clickable((By.XPATH,"//td[@data-handler='selectDay']/a[text()='11']")))
            day_element.click()

            time.sleep(1)

            apply_button = wait.until(EC.element_to_be_clickable((By.XPATH,"//button[contains(., 'Применить')]")))
            apply_button.click()

            time.sleep(1)

            download_btn = wait.until(EC.element_to_be_clickable((By.XPATH,"//a[contains(@class,'export') and contains(., 'XLSX')]")))
            driver.execute_script("arguments[0].click();",download_btn)
            time.sleep(3)

            files = [f for f in os.listdir(download_dir) if f.endswith(".xlsx")]

            if files:
                old_file = os.path.join(download_dir, files[0])
                new_filename = "ruonia.xlsx"
                new_file = os.path.join(download_dir, new_filename)
                os.rename(old_file, new_file)
        finally:
            driver.quit()

parser = RuoniaParser()
parser.parse()