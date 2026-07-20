from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from market_connector.adapters.deribit.errors import DeribitMappingError


DeribitBookSide = Literal['bid', 'ask']
DeribitBookUpdateType = Literal['snapshot']


@dataclass(frozen=True, slots=True)
class DeribitBookLevel:
    '''
    Normalized Deribit order-book level.
    '''

    side: DeribitBookSide
    price: Decimal
    volume: Decimal

    def to_dict(self) -> dict[str, Any]:
        '''
        Return this level as a plain dictionary.
        '''

        return {
            'side': self.side,
            'price': self.price,
            'volume': self.volume,
        }


@dataclass(frozen=True, slots=True)
class DeribitBookUpdate:
    '''
    Normalized Deribit grouped order-book snapshot.
    '''

    instrument_name: str
    timestamp: int
    change_id: int
    bids: tuple[DeribitBookLevel, ...]
    asks: tuple[DeribitBookLevel, ...]
    exchange: Literal['deribit'] = 'deribit'
    type: DeribitBookUpdateType = 'snapshot'

    @property
    def levels(self) -> tuple[DeribitBookLevel, ...]:
        '''
        Return bid and ask levels in payload order.
        '''

        return self.bids + self.asks

    @property
    def is_snapshot(self) -> Literal[True]:
        '''
        Return whether this update represents a book snapshot.
        '''

        return True

    def to_dict(self) -> dict[str, Any]:
        '''
        Return this update as a plain dictionary.
        '''

        return {
            'exchange': self.exchange,
            'instrument_name': self.instrument_name,
            'timestamp': self.timestamp,
            'change_id': self.change_id,
            'type': self.type,
            'bids': [level.to_dict() for level in self.bids],
            'asks': [level.to_dict() for level in self.asks],
        }


class DeribitMapper:
    '''
    Mapper for Deribit exchange payloads.
    '''

    @classmethod
    def book_snapshot(cls, payload: Mapping[str, Any]) -> DeribitBookUpdate:
        '''
        Map a grouped Deribit order-book snapshot payload.

        Supported channels use the `book.(instrument_name).(group).(depth).(interval)`
        shape, where `bids` and `asks` contain `[price, amount]` rows.
        '''

        if not isinstance(payload, Mapping):
            raise DeribitMappingError('Deribit book payload must be an object')

        return DeribitBookUpdate(
            instrument_name=cls._required_string(
                payload.get('instrument_name'),
                field='instrument_name',
            ),
            timestamp=cls._required_int(
                payload.get('timestamp'),
                field='timestamp',
            ),
            change_id=cls._required_int(
                payload.get('change_id'),
                field='change_id',
            ),
            bids=cls._book_levels(
                payload.get('bids'),
                side='bid',
                field='bids',
            ),
            asks=cls._book_levels(
                payload.get('asks'),
                side='ask',
                field='asks',
            ),
        )

    @classmethod
    def book_update(cls, payload: Mapping[str, Any]) -> DeribitBookUpdate:
        '''
        Map a grouped Deribit order-book snapshot payload.
        '''

        return cls.book_snapshot(payload)

    @classmethod
    def map_book_update(cls, payload: Mapping[str, Any]) -> DeribitBookUpdate:
        '''
        Map a grouped Deribit order-book snapshot payload.
        '''

        return cls.book_snapshot(payload)

    @classmethod
    def map_order_book_update(
        cls,
        payload: Mapping[str, Any],
    ) -> DeribitBookUpdate:
        '''
        Map a grouped Deribit order-book snapshot payload.
        '''

        return cls.book_snapshot(payload)

    @classmethod
    def book_snapshot_dict(cls, payload: Mapping[str, Any]) -> dict[str, Any]:
        '''
        Map a grouped Deribit order-book snapshot payload to a plain dictionary.
        '''

        return cls.book_snapshot(payload).to_dict()

    @classmethod
    def book_update_dict(cls, payload: Mapping[str, Any]) -> dict[str, Any]:
        '''
        Map a grouped Deribit order-book snapshot payload to a plain dictionary.
        '''

        return cls.book_snapshot_dict(payload)

    @classmethod
    def _book_levels(
        cls,
        value: Any,
        *,
        side: DeribitBookSide,
        field: str,
    ) -> tuple[DeribitBookLevel, ...]:
        rows = cls._required_sequence(value, field=field)
        levels: list[DeribitBookLevel] = []

        for index, row in enumerate(rows):
            levels.append(
                cls._book_level(
                    row,
                    side=side,
                    field=f'{field}[{index}]',
                )
            )

        return tuple(levels)

    @classmethod
    def _book_level(
        cls,
        value: Any,
        *,
        side: DeribitBookSide,
        field: str,
    ) -> DeribitBookLevel:
        row = cls._required_sequence(value, field=field)

        if len(row) != 2:
            raise DeribitMappingError(f'{field} must contain [price, amount]')

        return DeribitBookLevel(
            side=side,
            price=cls._decimal(
                row[0],
                field=f'{field}[0]',
                minimum=Decimal('0'),
                include_minimum=False,
            ),
            volume=cls._decimal(
                row[1],
                field=f'{field}[1]',
                minimum=Decimal('0'),
                include_minimum=True,
            ),
        )

    @staticmethod
    def _required_sequence(value: Any, *, field: str) -> Sequence[Any]:
        if isinstance(value, str | bytes | bytearray) or not isinstance(
            value,
            Sequence,
        ):
            raise DeribitMappingError(f'{field} must be a list')

        return value

    @staticmethod
    def _required_string(value: Any, *, field: str) -> str:
        if not isinstance(value, str):
            raise DeribitMappingError(f'{field} must be a string')

        value = value.strip()
        if not value:
            raise DeribitMappingError(f'{field} is required')

        return value

    @staticmethod
    def _required_int(value: Any, *, field: str) -> int:
        if type(value) is not int:
            raise DeribitMappingError(f'{field} must be an integer')

        return value

    @staticmethod
    def _decimal(
        value: Any,
        *,
        field: str,
        minimum: Decimal,
        include_minimum: bool,
    ) -> Decimal:
        if isinstance(value, bool) or value is None:
            raise DeribitMappingError(f'{field} must be a number')

        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise DeribitMappingError(f'{field} must be a number') from exc

        if not number.is_finite():
            raise DeribitMappingError(f'{field} must be a finite number')

        if include_minimum:
            is_valid = number >= minimum
            description = f'>= {minimum}'
        else:
            is_valid = number > minimum
            description = f'> {minimum}'

        if not is_valid:
            raise DeribitMappingError(f'{field} must be {description}')

        return number


__all__ = [
    'DeribitBookLevel',
    'DeribitBookSide',
    'DeribitBookUpdate',
    'DeribitBookUpdateType',
    'DeribitMapper',
    'DeribitMappingError',
]
