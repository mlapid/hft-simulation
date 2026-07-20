import pytest

from market_connector.adapters.deribit.channels import (
    DeribitChannelError,
    DeribitChannels,
)


def test_builds_public_market_channels():
    assert DeribitChannels.book('btc-perpetual') == 'book.BTC-PERPETUAL.none.10.100ms'


def test_rejects_empty_or_dotted_identifiers():
    with pytest.raises(DeribitChannelError, match='instrument_name is required'):
        DeribitChannels.book('  ')

    with pytest.raises(DeribitChannelError, match='cannot contain'):
        DeribitChannels.book('BTC.PERPETUAL')
