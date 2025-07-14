import logging
import re

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)

logger = logging.getLogger()

class TelegramHttpxFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        if match := re.search(r'https://api\.telegram\.org/bot[^/]+(/[^ ]+) "HTTP/1\.1 (\d{3})', msg):
            record.msg = f"{match.group(1)} - {match.group(2)}"
            record.args = ()
        return True

def install_telegram_http_filter():
    tg_filter = TelegramHttpxFilter()
    logging.getLogger().addFilter(tg_filter)
    for logger_obj in logging.root.manager.loggerDict.values():
        if isinstance(logger_obj, logging.Logger):
            logger_obj.addFilter(tg_filter)
