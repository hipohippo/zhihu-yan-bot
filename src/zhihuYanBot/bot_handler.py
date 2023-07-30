import asyncio
import logging
import re

from selenium.webdriver.common.by import By
from telegram import Update
from telegram.ext import ContextTypes

from hipo_telegram_bot_common.html_util.html_util import paragraphs_to_html
from hipo_telegram_bot_common.telegraph_publisher.publisher import publish_single
from zhihuYanBot.font_swap import build_swapped_char_map
from zhihuYanBot.zhihu_yan_bot_config import ZhihuYanBotConfig


async def scrape_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_config: ZhihuYanBotConfig = context.bot_data["bot_config"]
    if (not update) or (not update.message) or (not update.message.reply_to_message):
        logging.error("invalid input")
    zhihu_url = update.message.reply_to_message.text
    telegraph_url = None
    try:
        # title, paragraphs, soup = extract_content(bot_config.browser, url)
        bot_config.browser.get(zhihu_url)
        if re.match("https://www.zhihu.com/question/[\d]+/answer/[\d]+", zhihu_url):
            ## h1 Question-title does not
            title = (
                bot_config.browser.find_element(by=By.XPATH, value='//a[@role="pagedescription"]')
                .get_attribute("aria-label")[5:]
                .split("-")[0]
            )
            content_xpath = r'//div[@class="Card AnswerCard css-0"]'
            main_answer = bot_config.browser.find_element(by=By.XPATH, value=content_xpath)
            html_content = paragraphs_to_html(
                [v.text for v in main_answer.find_elements(by=By.CSS_SELECTOR, value="p")]
            )
        elif re.match("https://www.zhihu.com/market/paid_column/[\d]+/section/[\d]+", zhihu_url):
            title = bot_config.browser.find_element(
                by=By.XPATH, value=r'//h1[@class="ManuscriptTitle-root-gcmVk"]'
            ).text
            content_xpath = r'//div[@id="manuscript"]'
            main_answer = bot_config.browser.find_element(by=By.XPATH, value=content_xpath)
            html_content = paragraphs_to_html(
                [v.text for v in main_answer.find_elements(by=By.CSS_SELECTOR, value="p")]
            )
            swap_char_map = build_swapped_char_map(bot_config.browser)
            html_content = "".join([swap_char_map.get(c, c) for c in html_content])
        else:
            await update.message.reply_text("invalid url")
            return

        # soup = BeautifulSoup(main_answer, parser="html.parser", features="lxml")
        # title, paragraphs = extract_from_soup(soup)
        # dom = etree.HTML(str(soup))
        # title = dom.xpath(r'//h1[@class="QuestionHeader-title"]')[0].text
        # logging.info(f"{paragraphs[0]}, {paragraphs[-1]}")
        # html_content = paragraphs_to_html(paragraphs)
        # logging.info(f"{title}, {html_content[0:100]}, {html_content[-100:-1]}")
        # logging.info(f"html length {len(html_content)}")
        telegraph_url = publish_single(bot_config.telegraph_publisher, title, html_content)
    except Exception as e:
        error_message = f"failed in chat {update.effective_chat.id}: {e}"
        logging.error(error_message)
        await context.bot.send_message(bot_config.error_notify_chat, text=error_message)
        await asyncio.sleep(5)

    if telegraph_url:
        await update.message.reply_html(telegraph_url)
    return telegraph_url
