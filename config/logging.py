import logging
import re

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

class TelegramHttpxFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        # Target the specific HTTP request pattern from Telegram API
        if 'HTTP Request:' in msg and 'api.telegram.org' in msg:
            if match := re.search(r'POST https://api\.telegram\.org/bot[^/]+(/[^ ]+) "HTTP/1\.1 (\d{3})', msg):
                record.msg = f"Telegram API: {match.group(1)} - {match.group(2)}"
                record.args = ()
        return True

def install_telegram_http_filter():
    """Install filter on specific loggers that generate HTTP logs"""
    tg_filter = TelegramHttpxFilter()
    
    # Target specific loggers that generate HTTP requests
    target_loggers = ['httpx', 'telegram.ext', 'telegram']
    
    for logger_name in target_loggers:
        target_logger = logging.getLogger(logger_name)
        target_logger.addFilter(tg_filter)
