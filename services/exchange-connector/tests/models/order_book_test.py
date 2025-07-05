import uuid
import json

import pytest

from exchange_connector.models.order_book import OrderBook


class TestOrderBook:

    @pytest.fixture(scope="function")
    def order_book(self) -> OrderBook:
        return OrderBook(
            session_id=str(uuid.uuid1()),
            timestamp=1739524537.4823868,
            instrument_name='ETH-PERPETUAL',
            bids=[[10001, 10], [10000, 5]],
            asks=[[10002, 10], [10003, 5]],
        )
    
    def test_idempotency(self, order_book: OrderBook):
        order_book_json = order_book.model_dump_json()
        assert order_book == OrderBook(**json.loads(order_book_json))