from decimal import Decimal

import pytest

from market_connector.adapters.deribit.mapper import (
    DeribitBookLevel,
    DeribitMapper,
    DeribitMappingError,
)


def test_maps_grouped_book_snapshot_payload():
    update = DeribitMapper.book_snapshot({
        'timestamp': 1554375447971,
        'instrument_name': 'BTC-PERPETUAL',
        'change_id': 109615,
        'bids': [
            [160, 40],
            ['159.5', '20.25'],
        ],
        'asks': [
            [161, 20],
        ],
    })

    assert update.exchange == 'deribit'
    assert update.instrument_name == 'BTC-PERPETUAL'
    assert update.timestamp == 1554375447971
    assert update.change_id == 109615
    assert update.type == 'snapshot'
    assert update.is_snapshot is True
    assert update.bids == (
        DeribitBookLevel(
            side='bid',
            price=Decimal('160'),
            volume=Decimal('40'),
        ),
        DeribitBookLevel(
            side='bid',
            price=Decimal('159.5'),
            volume=Decimal('20.25'),
        ),
    )
    assert update.asks == (
        DeribitBookLevel(
            side='ask',
            price=Decimal('161'),
            volume=Decimal('20'),
        ),
    )
    assert update.levels == update.bids + update.asks


def test_book_update_alias_maps_grouped_book_snapshot_payload():
    update = DeribitMapper.book_update({
        'timestamp': 1554375447971,
        'instrument_name': 'ETH-PERPETUAL',
        'change_id': 109615,
        'bids': [[160, 40]],
        'asks': [[161, 20]],
    })

    assert update.type == 'snapshot'
    assert update.bids == (
        DeribitBookLevel(
            side='bid',
            price=Decimal('160'),
            volume=Decimal('40'),
        ),
    )
    assert update.asks == (
        DeribitBookLevel(
            side='ask',
            price=Decimal('161'),
            volume=Decimal('20'),
        ),
    )


def test_book_snapshot_dict_returns_plain_mapping():
    mapped = DeribitMapper.book_snapshot_dict({
        'timestamp': 1554375447971,
        'instrument_name': 'ETH-PERPETUAL',
        'change_id': 109615,
        'bids': [[160, 40]],
        'asks': [[161, 20]],
    })

    assert mapped == {
        'exchange': 'deribit',
        'instrument_name': 'ETH-PERPETUAL',
        'timestamp': 1554375447971,
        'change_id': 109615,
        'type': 'snapshot',
        'bids': [
            {
                'side': 'bid',
                'price': Decimal('160'),
                'volume': Decimal('40'),
            }
        ],
        'asks': [
            {
                'side': 'ask',
                'price': Decimal('161'),
                'volume': Decimal('20'),
            }
        ],
    }


@pytest.mark.parametrize(
    ('payload', 'message'),
    [
        ({}, 'instrument_name must be a string'),
        ({
            'instrument_name': 'BTC-PERPETUAL',
            'timestamp': 1,
            'change_id': 2,
            'bids': 'bad',
            'asks': [],
        }, 'bids must be a list'),
        ({
            'instrument_name': 'BTC-PERPETUAL',
            'timestamp': 1,
            'change_id': 2,
            'bids': [['new', 100, 1]],
            'asks': [],
        }, 'bids\\[0\\] must contain \\[price, amount\\]'),
        ({
            'instrument_name': 'BTC-PERPETUAL',
            'timestamp': 1,
            'change_id': 2,
            'bids': [[0, 1]],
            'asks': [],
        }, 'bids\\[0\\]\\[0\\] must be > 0'),
        ({
            'instrument_name': 'BTC-PERPETUAL',
            'timestamp': 1,
            'change_id': 2,
            'bids': [[100, -1]],
            'asks': [],
        }, 'bids\\[0\\]\\[1\\] must be >= 0'),
    ],
)
def test_rejects_malformed_book_snapshot_payload(payload, message):
    with pytest.raises(DeribitMappingError, match=message):
        DeribitMapper.book_snapshot(payload)
