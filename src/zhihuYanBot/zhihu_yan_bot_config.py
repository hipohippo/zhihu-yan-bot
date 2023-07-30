from configparser import SectionProxy
from typing import Union

from telegraph import Telegraph

from hipo_telegram_bot_common.bot_config.bot_config import BotConfig
from hipo_telegram_bot_common.selenium_driver.launch import get_chrome_driver
from hipo_telegram_bot_common.util import format_white_list


class ZhihuYanBotConfig(BotConfig):
    """
    required field

    chromedriver_path
    chrome_driver
    given_port
    max_web_driver_window

    telegraph token

    """

    def __init__(self, bot_config_dict: Union[dict, SectionProxy]):
        super().__init__(
            int(bot_config_dict["heart_beat_chat"]),
            int(bot_config_dict["error_notify_chat"]),
            white_list_id=format_white_list(bot_config_dict["white_list"]),
            bot_name="Zhihu Yan Bot",
        )
        self.browser = get_chrome_driver(
            bot_config_dict, load_extension=False, given_port=int(bot_config_dict["given_port"])
        )
        self.telegraph_publisher = Telegraph(access_token=bot_config_dict["telegraph_token"])
