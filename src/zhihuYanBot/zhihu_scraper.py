from bs4 import BeautifulSoup
from selenium.webdriver.chrome.webdriver import WebDriver


def scrape(browser: WebDriver, url: str) -> str:
    browser.get(url)
    soup = BeautifulSoup(browser)


def decode_zhihu_paid_column():
    pass