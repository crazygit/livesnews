# -*- coding: utf-8 -*-
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List

import requests
from environs import Env
from requests.cookies import RequestsCookieJar
from telegram.error import (
    TelegramError,
    Unauthorized,
    BadRequest,
    TimedOut,
    ChatMigrated,
    NetworkError,
)
from telegram.ext import (
    CallbackContext,
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

requests_headers = {
    "User-Agent": "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:70.0) Gecko/20100101 Firefox/70.0",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://xueqiu.com/today/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
}


@dataclass(frozen=True)
class News:
    """新闻信息的数据封装类"""

    id: int
    text: str
    mark: int
    target: str = field(repr=False)
    created_at: int

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, News):
            return NotImplemented
        return self.id == other.id

    def to_markdown(self) -> str:
        return f"""
{escape_text(self.text)}

{escape_text(datetime.fromtimestamp(self.created_at / 1000, tz=timezone(timedelta(hours=8))).strftime('(%Y-%m-%d %H:%M)'))}
"""


def get_news() -> List[News]:
    url = "https://xueqiu.com/v4/statuses/public_timeline_by_category.json"
    logger.info("Query news from XueQiu")
    response = requests.get(
        url,
        params={"since_id": -1, "max_id": -1, "count": 10, "category": 6},
        headers=requests_headers,
        cookies=get_cookie(),
    )
    news_list = []
    if response.status_code == 200:
        for item in response.json().get("list", []):
            item = json.loads(item["data"])
            news_list.append(
                News(
                    id=item["id"],
                    text=item["text"],
                    mark=item["mark"],
                    target=item["target"],
                    created_at=item["created_at"],
                )
            )
    else:
        logger.warning("Get news failed")
        logger.error(response.text)
    return news_list


def get_cookie() -> RequestsCookieJar:
    logger.info("get cookies")
    url = "https://xueqiu.com/?category=livenews"
    response = requests.get(url, headers=requests_headers)
    return response.cookies


def start(updater: Updater, context: CallbackContext) -> None:
    updater.message.reply_text("I'm a bot, please talk to me!")


def unknown(update: Updater, context: CallbackContext) -> None:
    update.message.reply_text("Sorry, I didn't understand that command.")


def escape_text(text: str) -> str:
    if text:
        for keyword in [
            "_",
            "*",
            "[",
            "]",
            "(",
            ")",
            "~",
            "`",
            ">",
            "#",
            "+",
            "-",
            "=",
            "|",
            "{",
            "}",
            ".",
            "!",
        ]:
            text = text.replace(keyword, f"\\{keyword}")
        return text
    return ""


def send_news_message(context: CallbackContext) -> None:
    try:
        chat_id = context.job.context.get("channel_id")
        interval = context.job.context.get("interval")
        news_list = get_news()
        if news_list:
            # 按照时间先后排序
            news_list.reverse()
            for news in news_list:
                if news.created_at + interval * 1000 >= int(time.time() * 1000):
                    logger.info(f"send message: {news.to_markdown()}")
                    context.bot.send_message(
                        chat_id=chat_id,
                        parse_mode="MarkdownV2",
                        text=news.to_markdown(),
                        disable_web_page_preview=True,
                    )
                else:
                    logger.info(f"Repeated message: {news.to_markdown()}")
        else:
            logger.info(f"No news in latest {interval} seconds")
    except Exception as e:
        logger.exception(e)


def error_callback(update: Updater, context: CallbackContext) -> None:
    try:
        raise context.error
    except Unauthorized as e:
        # remove update.message.chat_id from conversation list
        logger.error(e)
    except BadRequest as e:
        # handle malformed requests - read more below!
        logger.error(e)
    except TimedOut as e:
        # handle slow connection problems
        logger.error(e)
    except NetworkError as e:
        # handle other connection problems
        logger.error(e)
    except ChatMigrated as e:
        # the chat_id of a group has changed, use e.new_chat_id instead
        logger.error(e)
    except TelegramError as e:
        # handle all other telegram related errors
        logger.error(e)


def main() -> None:
    env = Env()
    # Read .env into os.environ
    env.read_env()
    # 每隔两分钟检查一次是否有新消息
    interval = 60 * 2  # seconds

    token = env.str("BOT_TOKEN", None)
    channel_id = env.str("CHANNEL_ID", None)
    assert token is not None, "Please Set Bot Token"
    assert channel_id is not None, "Please Set Channel id"
    # channel_id必须以@符号开头
    if not channel_id.startswith("@"):
        channel_id = f"@{channel_id}"

    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher
    updater.job_queue.run_repeating(
        send_news_message,
        interval,
        first=0,
        context={"channel_id": channel_id, "interval": interval},
    )
    start_handler = CommandHandler("start", start)
    dispatcher.add_handler(start_handler)

    # This handler must be added last. If you added it sooner, it would be triggered before the CommandHandlers had a chance to look at the update. Once an update is handled, all further handlers are ignored.
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)
    dispatcher.add_error_handler(error_callback)

    updater.start_polling()
    logger.info("Started Bot...")
    updater.idle()


if __name__ == "__main__":
    main()
