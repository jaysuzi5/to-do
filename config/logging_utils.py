import json
import logging
import traceback


class JsonFormatter(logging.Formatter):
    def format(self, record):
        if record.getMessage().startswith('{'):
            try:
                return record.getMessage()
            except Exception:
                pass
        log = {
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        if record.exc_info:
            log['traceback'] = traceback.format_exception(*record.exc_info)
        return json.dumps(log)
