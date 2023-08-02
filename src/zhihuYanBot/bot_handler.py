import asyncio
import logging
import re
from typing import List

from telegram import Update
from telegram.ext import ContextTypes
import traceback
from hipo_telegram_bot_common.telegraph_publisher.publisher import publish_chunk
from zhihuYanBot.scrape import extract_zhihu_content, extract_protected_weibo_content
from zhihuYanBot.zhihu_yan_bot_config import ZhihuYanBotConfig


async def scrape_protected_weibo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_config: ZhihuYanBotConfig = context.bot_data["bot_config"]
    if (not update) or (not update.message) or (not update.message.reply_to_message):
        logging.error("invalid input")
        return

    url = update.message.reply_to_message.text
    telegraph_url = None
    if not re.match(r"https://(m.)?weibo.((com)|(cn))/.+", url):
        await update.message.reply_html("unsupported url")
        return

    try:
        author, html_content = extract_protected_weibo_content(bot_config.browser, url)
        # telegraph_url = publish_single(bot_config.telegraph_publisher, author + "的微博", html_content)
        await update.message.reply_html(f"from {author}\n {html_content}")
    except Exception as e:
        error_message = f"failed in chat {update.effective_chat.id}: {e}"
        logging.error(error_message)
        await context.bot.send_message(bot_config.error_notify_chat, text=error_message)
        await asyncio.sleep(5)
    return telegraph_url


async def scrape_zhihu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_config: ZhihuYanBotConfig = context.bot_data["bot_config"]
    if (not update) or (not update.message) or (not update.message.reply_to_message):
        logging.error("invalid input")
        await update.message.reply_html("empty message")

    url = update.message.reply_to_message.text
    telegraph_urls = None
    if not re.match(r"https://www.zhihu.com/.+", url):
        await update.message.reply_html("unsupported url")
        return

    try:
        title, html_content_group = extract_zhihu_content(bot_config.browser, url)
        if not title:
            await update.message.reply_text("unsupported url")
            return
        logging.info(sum([len(s) for s in html_content_group]))
        # telegraph_url = publish_single(bot_config.telegraph_publisher, title, html_content)
        telegraph_urls: List[str] = publish_chunk(bot_config.telegraph_publisher, title, html_content_group)
    except Exception as e:
        error_message = f"failed in chat {update.effective_chat.id}: {traceback.format_exc()}"
        logging.error(error_message)
        await context.bot.send_message(bot_config.error_notify_chat, text=error_message)
        await asyncio.sleep(5)

    if telegraph_urls:
        await update.message.reply_html("\n".join(telegraph_urls))
    return telegraph_urls
