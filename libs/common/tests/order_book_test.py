import pytest

import json
import uuid
from datetime import datetime, timezone

from common.order_book import OrderBook


class TestOrderBook:

    @pytest.fixture(scope="function")
    def order_book(self) -> OrderBook:
        return OrderBook(
            session_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            instrument_name='ETH-PERPETUAL',
            bids=[[10001, 10], [10000, 5]],
            asks=[[10002, 10], [10003, 5]],
        )
    
    def test_idempotency(self, order_book: OrderBook):
        order_book_json: dict = json.loads(order_book.model_dump_json())
        assert order_book == OrderBook(**order_book_json)

    def test_best_bid(self, order_book: OrderBook):
        assert order_book.best_bid == (10001, 10)

    def test_best_ask(self, order_book: OrderBook):
        assert order_book.best_ask == (10002, 10)