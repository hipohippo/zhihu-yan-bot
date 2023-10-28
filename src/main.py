# -*- coding: utf-8 -*-


import logging
import sys

from telegram.ext import Application, MessageHandler, filters

from hipo_telegram_bot_common.bot_config.bot_config_parser import parse_from_ini
from hipo_telegram_bot_common.bot_factory import BotBuilder
from hipo_telegram_bot_common.common_handler import heart_beat_job
from zhihu_yan_bot.bot_handler import scrape_zhihu_handler, scrape_protected_weibo_handler
from zhihu_yan_bot.zhihu_yan_bot_config import ZhihuYanBotConfig


def build_bot_app(bot_config_dict) -> Application:
    bot_config = ZhihuYanBotConfig(bot_config_dict)
    bot_app = (
        BotBuilder(bot_config_dict["bot_token"], bot_config)
        .add_handlers([MessageHandler(filters.Regex("^/zhihu"), scrape_zhihu_handler),])
        .add_handlers([MessageHandler(filters.Regex("^/weibo"), scrape_protected_weibo_handler),])
        .add_repeating_jobs([(heart_beat_job, {"first": 5, "interval": 3 * 3600})])
        .build()
    )
    return bot_app


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO, encoding="utf-8")
    bot_config_file = sys.argv[1]
    bot_config_dict = parse_from_ini(bot_config_file)
    bot_app = build_bot_app(bot_config_dict)
    bot_app.run_polling()

    """
    TODO: emulate QR code login
    """
