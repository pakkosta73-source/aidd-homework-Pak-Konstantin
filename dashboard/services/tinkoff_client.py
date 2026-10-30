from contextlib import contextmanager

from config.settings import TINKOFF_TOKEN, USE_TINKOFF_MOCK

from .mock_tinkoff import MockTinkoffClient


@contextmanager
def get_client():
    """Контекстный менеджер для подключения к Tinkoff Invest API.

    Если USE_TINKOFF_MOCK=True, возвращает заглушку с тестовыми данными.
    """
    if USE_TINKOFF_MOCK:
        with MockTinkoffClient() as client:
            yield client
    else:
        from tinkoff.invest import Client
        with Client(TINKOFF_TOKEN) as client:
            yield client
