"""Построение графика исторических цен акции (последние 180 дней, Plotly)."""

from datetime import timedelta

from plotly.graph_objs import Scatter
from plotly.offline import plot
from tinkoff.invest import CandleInterval
from tinkoff.invest.utils import now

from dashboard.services.market_data import quotation_to_float
from dashboard.services.tinkoff_client import tinkoff_client


def get_graph(share, days: int = 180):
    """Div-разметка графика цен закрытия (close).

    - Открытие клиента вынесено в общий `tinkoff_client`
      (раньше здесь создавался свой `Client(TINKOFF_TOKEN)`).
    - `include_plotlyjs=False`: библиотека уже подключена в base.html,
      иначе plotly инлайнил ~3 МБ JS в каждую страницу.
    - Цены берутся из units + nano (раньше округлялись до рублей).
    """
    with tinkoff_client() as client:
        x_data, y_data = [], []
        for candle in client.get_all_candles(
            figi=share.figi,
            from_=now() - timedelta(days=days),
            interval=CandleInterval.CANDLE_INTERVAL_DAY,
        ):
            x_data.append(candle.time.date())
            y_data.append(quotation_to_float(candle.close))

    return plot(
        [
            Scatter(
                x=x_data,
                y=y_data,
                mode="lines",
                name=share.ticker,
                opacity=0.8,
                marker_color="red",
            )
        ],
        output_type="div",
        show_link=False,
        link_text="",
        include_plotlyjs=False,
    )
