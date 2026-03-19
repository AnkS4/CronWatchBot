import logging
import re
from typing import List

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

class TelegramHttpxFilter(logging.Filter):
    """Filter to simplify Telegram HTTP request logs."""
    
    _pattern = re.compile(r'POST https://api\.telegram\.org/bot[^/]+(/[^ ]+) "HTTP/1\.1 (\d{3})')
    
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if 'HTTP Request:' in msg and 'api.telegram.org' in msg:
            if match := self._pattern.search(msg):
                record.msg = f"Telegram API: {match.group(1)} - {match.group(2)}"
                record.args = ()
        return True

def install_telegram_http_filter() -> None:
    """Install filter on specific loggers that generate HTTP logs."""
    tg_filter = TelegramHttpxFilter()
    target_loggers: List[str] = ['httpx', 'telegram.ext', 'telegram']
    
    for logger_name in target_loggers:
        logging.getLogger(logger_name).addFilter(tg_filter)
