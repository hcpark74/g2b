import logging

import pytest


@pytest.fixture(autouse=True)
def suppress_sqlalchemy_logs() -> None:
    engine_logger = logging.getLogger("sqlalchemy.engine")
    pool_logger = logging.getLogger("sqlalchemy.pool")
    previous_engine_level = engine_logger.level
    previous_pool_level = pool_logger.level

    engine_logger.setLevel(logging.WARNING)
    pool_logger.setLevel(logging.WARNING)

    yield

    engine_logger.setLevel(previous_engine_level)
    pool_logger.setLevel(previous_pool_level)
