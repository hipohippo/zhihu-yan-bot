import re
from typing import Tuple, Optional, List

from bs4 import BeautifulSoup
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from zhihuYanBot.font_swap import build_swapped_char_map


def extract_protected_weibo_content(browser: WebDriver, url: str) -> Tuple[str, str]:
    browser.get(url)
    main_answer = browser.find_element(by=By.XPATH, value='//div[@class="weibo-text"]').text
    author = browser.find_element(by=By.XPATH, value='//h3[@class="m-text-cut"]').text
    return author, main_answer


def extract_zhihu_content(browser: WebDriver, url: str) -> Tuple[Optional[str], Optional[List[str]]]:
    if re.match("https://www.zhihu.com/question/[\d]+/answer/[\d]+", url):
        url_type = "answer"
        url = url.split("?")[0]
        browser.get(url)
        ## h1 Question-title does not
        title = (
            browser.find_element(by=By.XPATH, value='//a[@role="pagedescription"]')
            .get_attribute("aria-label")[5:]
            .split("-")[0]
        )
        content_xpath = r'//div[@class="Card AnswerCard css-0"]'  ## xpath is url sensitive
        main_answer = browser.find_element(by=By.XPATH, value=content_xpath)
        soup = BeautifulSoup(main_answer.get_attribute("outerHTML"), features="lxml")
        html_content_group = clean_html_for_answer(soup)

    elif re.match("https://www.zhihu.com/market/paid_column/[\d]+/section/[\d]+", url):
        url_type = "paid_column"
        url = url.split("?")[0]
        browser.get(url)
        title = browser.find_element(
            by=By.XPATH, value=r'//h1[@class="ManuscriptTitle-root-gcmVk"]'
        ).text  ## xpath is url sensitive
        content_xpath = r'//div[@id="manuscript"]'
        ## reverse engineer char map. this line must be exectued here before building soup
        swap_char_map = build_swapped_char_map(browser)

    else:
        return None, None
    main_answer = browser.find_element(by=By.XPATH, value=content_xpath)
    soup = BeautifulSoup(main_answer.get_attribute("outerHTML"), features="lxml")
    html_content_group = clean_html_for_answer(soup)
    if url_type == "paid_column":
        html_content_group = [
            "".join([swap_char_map.get(c, c) for c in html_content]) for html_content in html_content_group
        ]

    return title, html_content_group


def clean_html_for_answer(soup: BeautifulSoup) -> List[str]:
    vv = soup.find_all(["p", "img"])
    html = []
    for element in vv:
        if element.name == "p":
            html.append(f"<p> {element.text} \n </p>")
            if element.text.find("备案号") >= 0:
                break
        elif element.name == "img":
            for src_attribute in {"src", "data-src"}:
                img_src = element.get(src_attribute)
                if type(img_src) == str and re.match(r"https://pic[0-9a-zA-Z].zhimg.com/v2.+", img_src):
                    img_height = element.get("height")
                    img_width = element.get("width")
                    html.append(f'<img src="{img_src}" height={img_height} width={img_width}/>')
    return html
