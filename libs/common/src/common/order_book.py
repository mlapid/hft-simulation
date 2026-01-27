from typing import Annotated
from datetime import datetime, timezone

from sortedcontainers import SortedDict
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_validator
)


class OrderBook(BaseModel):
    model_config = ConfigDict(
        title='OrderBook',
        frozen=False,
        arbitrary_types_allowed=True
    )

    session_id:      Annotated[str, Field(alias='session_id', description='Session ID')]
    timestamp:       Annotated[datetime, Field(alias='timestamp', description='Timestamp of the order book in UTC timezone')]
    instrument_name: Annotated[str, Field(alias='instrument_name', description='Instrument name')]
    bids:            Annotated[SortedDict[float, float], Field(alias='bids', description='Bids, sorted by price in ascending order')]
    asks:            Annotated[SortedDict[float, float], Field(alias='asks', description='Asks, sorted by price in ascending order')]

    @field_validator('timestamp', mode='before')
    def convert_timestamp_to_datetime(cls, v: float | str | datetime) -> datetime:
        if isinstance(v, float):
            return datetime.fromtimestamp(v, tz=None)
        elif isinstance(v, str):
            return datetime.fromisoformat(v)
        elif isinstance(v, datetime):
            return v
        raise ValueError(f'Invalid timestamp: {type(v)}')

    @field_validator('bids', mode='before')
    def convert_bids_to_sorted_dict(cls, v: list | dict) -> SortedDict[float, float]:
        if isinstance(v, list):
            return SortedDict([(float(v[0]), float(v[1])) for v in v])
        elif isinstance(v, dict):
            return SortedDict({float(k): float(v) for k, v in v.items()})
        raise ValueError(f'Invalid bids: {type(v)}')

    @field_validator('asks', mode='before')
    def convert_asks_to_sorted_dict(cls, v: list | dict) -> SortedDict[float, float]:
        if isinstance(v, list):
            return SortedDict([(float(v[0]), float(v[1])) for v in v])
        elif isinstance(v, dict):
            return SortedDict({float(k): float(v) for k, v in v.items()})
        raise ValueError(f'Invalid asks: {type(v)}')

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(' \
            f'session_id={self.session_id}, ' \
            f'timestamp={self.timestamp}, ' \
            f'instrument_name={self.instrument_name}, ' \
            f'bids={self.bids}, ' \
            f'asks={self.asks})'

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def best_bid(self) -> tuple[float, float]:
        return self.bids.peekitem(-1)

    @property
    def best_ask(self) -> tuple[float, float]:
        return self.asks.peekitem(0)

    @property
    def mid_price(self) -> float:
        return (self.best_bid[0] + self.best_ask[0]) / 2

    @property
    def spread(self) -> float:
        return self.best_ask[0] - self.best_bid[0]

    @property
    def volume_imbalance(self) -> float:
        return (self.best_bid[1] - self.best_ask[1]) / (self.best_bid[1] + self.best_ask[1])