import logging
from threading import Lock


'''
usage example:
logger1 = LoggerSingleton().get_logger()
logger2 = LoggerSingleton().get_logger()

logger1.info("This is a log message from logger1.")
logger2.debug("This is a debug message from logger2.")

check is it the same class instance
print(logger1 is logger2)  # True

'''

class LoggerSingleton:
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls, *args, **kwargs)
                    cls._instance._configure_logger()
        return cls._instance

    def _configure_logger(self):
        self.logger = logging.getLogger("SingletonLogger")
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)

    def get_logger(self):
        return self.logger

if __name__ == '__main__':
    logger = LoggerSingleton().get_logger()
