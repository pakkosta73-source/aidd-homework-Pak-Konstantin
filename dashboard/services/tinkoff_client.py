from contextlib import contextmanager

from tinkoff.invest import Client

from config.settings import TINKOFF_TOKEN


@contextmanager
def get_client():
    """Контекстный менеджер для подключения к Tinkoff Invest API."""
    with Client(TINKOFF_TOKEN) as client:
        yield client
