import hashlib
from .logger_singleton import LoggerSingleton

logger = LoggerSingleton().get_logger()


def hash_password(password):
    logger.debug(password)
    password_bytes = password.encode('utf-8')
    sha256_hash = hashlib.sha256(password_bytes).hexdigest()
    return password


def verify_password(password, hashed_password):
    logger.debug(password)
    return hash_password(password) == hashed_password
