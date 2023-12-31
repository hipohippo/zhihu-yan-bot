import logging
import re
from typing import Tuple, Optional, List, Dict

from bs4 import BeautifulSoup
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from zhihu_yan_bot.font_swap import build_swapped_char_map


def extract_protected_weibo_content(browser: WebDriver, url: str) -> Tuple[str, str]:
    browser.get(url)
    main_answer = browser.find_element(by=By.XPATH, value='//div[@class="weibo-text"]').text
    author = browser.find_element(by=By.XPATH, value='//h3[@class="m-text-cut"]').text
    return author, main_answer


def extract_zhihu_content(browser: WebDriver, url: str) -> Tuple[Optional[str], Optional[List[str]], Dict[str,str]]:
    char_swap_required = False
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
        if (soup.text.find("本内容版权为知乎及版权方所有") >= 0) or (soup.text.find("会员特权") >= 0 and soup.text.find("已解锁价值") >= 0):
            logging.getLogger(__name__).info("付费回答")
            char_swap_required = True
            swap_char_map = build_swapped_char_map(browser, url_type)
        else:
            logging.getLogger(__name__).info("非付费回答" + soup.text)

    elif re.match("https://www.zhihu.com/market/paid_column/[\d]+/section/[\d]+", url):
        char_swap_required = True
        url_type = "paid_column"
        logging.getLogger(__name__).info("付费专栏")
        url = url.split("?")[0]
        browser.get(url)
        title = browser.find_element(
            by=By.XPATH, value=r'//h1[@class="ManuscriptTitle-root-gcmVk"]'
        ).text  ## xpath is url sensitive
        content_xpath = r'//div[@id="manuscript"]'
        main_answer = browser.find_element(by=By.XPATH, value=content_xpath)
        soup = BeautifulSoup(main_answer.get_attribute("outerHTML"), features="lxml")
        html_content_group = clean_html_for_answer(soup)
        ## reverse engineer char map. swap must appear after getting main_answer
        swap_char_map = build_swapped_char_map(browser, url_type)
    else:
        return None, None

    if char_swap_required:
        html_content_group = [
            "".join([swap_char_map.get(c, c) for c in html_content]) for html_content in html_content_group
        ]

    return title, html_content_group, swap_char_map


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
