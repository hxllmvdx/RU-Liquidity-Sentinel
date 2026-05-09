from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os
from datetime import datetime
import time

class ReservesDownloader:
    def __init__(self):
        pass
    
    def parse(self):
        URL = "https://www.cbr.ru/hd_base/RReserves/"
        download_dir = os.path.join(os.getcwd(),"data","raw","cbr", "reserves")
        os.makedirs(download_dir, exist_ok=True)
        
        options = webdriver.ChromeOptions()

        prefs = {"download.default_directory": download_dir,"download.prompt_for_download": False, "download.directory_upgrade": True}

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
            
            element = wait.until(EC.element_to_be_clickable((By.XPATH,"//span[text()='Обязательные резервы']")))
            element.click()
            time.sleep(10)

        finally:
            driver.quit()


downloader = ReservesDownloader()
downloader.parse()