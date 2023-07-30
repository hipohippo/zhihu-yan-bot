import asyncio
import logging
from typing import List

from telegram import Update
from telegram.ext import ContextTypes

from hipo_telegram_bot_common.telegraph_publisher.publisher import publish_chunk
from zhihuYanBot.scrape import extract_content
from zhihuYanBot.zhihu_yan_bot_config import ZhihuYanBotConfig


async def scrape_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_config: ZhihuYanBotConfig = context.bot_data["bot_config"]
    if (not update) or (not update.message) or (not update.message.reply_to_message):
        logging.error("invalid input")
    zhihu_url = update.message.reply_to_message.text
    telegraph_urls = None

    try:
        title, html_content_group = extract_content(bot_config.browser, zhihu_url)
        if not title:
            await update.message.reply_text("invalid url")
            return
        logging.info(sum([len(s) for s in html_content_group]))
        # telegraph_url = publish_single(bot_config.telegraph_publisher, title, html_content)
        telegraph_urls: List[str] = publish_chunk(bot_config.telegraph_publisher, title, html_content_group)
    except Exception as e:
        error_message = f"failed in chat {update.effective_chat.id}: {e}"
        logging.error(error_message)
        await context.bot.send_message(bot_config.error_notify_chat, text=error_message)
        await asyncio.sleep(5)

    if telegraph_urls:
        await update.message.reply_html("\n".join(telegraph_urls))
    return telegraph_urls
