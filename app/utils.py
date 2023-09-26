from logging import Filter


# -----------------------------------------------------------------------------
class LogFilter(Filter):
    def filter(self, record):
        record.levelname = '[' + record.levelname +']'
        if record.threadName == 'AnyIO worker thread':
            record.threadName = 'AnyIO'
        return True
