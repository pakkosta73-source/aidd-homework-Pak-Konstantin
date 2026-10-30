from datetime import timedelta

from plotly.graph_objs import Scatter
from plotly.offline import plot
from tinkoff.invest import CandleInterval
from tinkoff.invest.utils import now

from .tinkoff_client import get_client

DAYS_BACK = 180


def get_graph(share):
    """Сгенерировать график исторических цен акции за последние DAYS_BACK дней."""
    x_data, y_data = [], []
    with get_client() as client:
        for candle in client.get_all_candles(
            figi=share.figi,
            from_=now() - timedelta(days=DAYS_BACK),
            interval=CandleInterval.CANDLE_INTERVAL_DAY,
        ):
            x_data.append(candle.time.date())
            y_data.append(candle.close.units)
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
    )
