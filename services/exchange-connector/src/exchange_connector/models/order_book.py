from typing import Annotated, Self
from datetime import datetime, timezone
from collections import namedtuple

from pydantic.config import ConfigDict
from pydantic import BaseModel, Field, field_validator, model_validator


Level = namedtuple('Level', ['price', 'volume'])

class OrderBook(BaseModel):
    model_config = ConfigDict(
        title='OrderBook',
        frozen=True,
        arbitrary_types_allowed=True
    )

    session_id:      Annotated[str, Field(alias='session_id', description='Session ID')]
    timestamp:       Annotated[datetime, Field(alias='timestamp', description='Timestamp of the order book in UTC timezone')]
    instrument_name: Annotated[str, Field(alias='instrument_name', description='Instrument name')]
    bids:            Annotated[list[Level[float, float]], Field(alias='bids', description='Bids, sorted by price in ascending order')]
    asks:            Annotated[list[Level[float, float]], Field(alias='asks', description='Asks, sorted by price in descending order')]

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(' \
            f'session_id={self.session_id}, ' \
            f'timestamp={self.timestamp}, ' \
            f'instrument_name={self.instrument_name}, ' \
            f'bids={self.bids}, ' \
            f'asks={self.asks})'

    def __repr__(self) -> str:
        return self.__str__()

    @field_validator('timestamp', mode='before')
    def convert_timestamp_to_datetime(cls, timestamp: float | datetime | str) -> datetime:
        if isinstance(timestamp, float):
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        elif isinstance(timestamp, datetime):
            return timestamp.astimezone(timezone.utc)
        elif isinstance(timestamp, str):
            return datetime.fromisoformat(timestamp).astimezone(timezone.utc)
        else:
            raise ValueError(f'Invalid timestamp: {timestamp}')

    @field_validator('bids', mode='before')
    def convert_bids_to_levels(cls, v: list[list[float, float]]) -> list[Level[float, float]]:
        return [Level(price=v[0], volume=v[1]) for v in v]

    @field_validator('asks', mode='before')
    def convert_asks_to_levels(cls, v: list[list[float, float]]) -> list[Level[float, float]]:
        return [Level(price=v[0], volume=v[1]) for v in v]


    @field_validator('bids', mode='after')
    def validate_bids(cls, v: list[Level[float, float]]) -> list[Level[float, float]]:
        for i in range(len(v) - 1):
            if v[i].price < v[i + 1].price:
                raise ValueError(f'Bids are not sorted: {v[i].price} < {v[i + 1].price}')
        return v

    @field_validator('asks', mode='after')
    def validate_asks(cls, v: list[Level[float, float]]) -> list[Level[float, float]]:
        for i in range(len(v) - 1):
            if v[i].price > v[i + 1].price:
                raise ValueError(f'Asks are not sorted: {v[i].price} > {v[i + 1].price}')
        return v

    @model_validator(mode='after')
    def validate_bids_asks_equal(self) -> Self:
        if len(self.bids) != len(self.asks):
            raise ValueError(f'Number of bids and asks must be equal, got {len(self.bids)} bids and {len(self.asks)} asks')
        return self