from market_connector.adapters.deribit.errors import (
    DeribitChannelError,
    DeribitConnectionError,
    DeribitError,
    DeribitInvalidParamsError,
    DeribitMappingError,
    DeribitNotFoundError,
    DeribitOrderError,
    DeribitOrderNotFoundError,
    DeribitRateLimitError,
    DeribitRpcError,
)


def test_deribit_rpc_error_uses_specific_subclass_by_message():
    error = DeribitRpcError.from_error({
        'code': 10028,
        'message': 'too_many_requests',
        'data': {'retry_after': 1},
    })

    assert isinstance(error, DeribitRateLimitError)
    assert isinstance(error, DeribitRpcError)
    assert isinstance(error, DeribitError)
    assert error.code == 10028
    assert error.message == 'too_many_requests'
    assert error.data == {'retry_after': 1}
    assert str(error) == 'Deribit RPC error 10028: too_many_requests'


def test_deribit_rpc_error_uses_specific_subclass_by_code():
    error = DeribitRpcError.from_error({
        'code': -32602,
    })

    assert isinstance(error, DeribitInvalidParamsError)
    assert error.code == -32602
    assert error.message == 'Unknown Deribit RPC error'


def test_deribit_adapter_errors_have_common_base():
    connection_error = DeribitConnectionError('connection failed')
    channel_error = DeribitChannelError('bad channel')
    mapping_error = DeribitMappingError('bad payload')
    order_not_found_error = DeribitOrderNotFoundError(
        code=10004,
        message='order_not_found',
    )

    assert isinstance(connection_error, DeribitError)
    assert isinstance(connection_error, ConnectionError)
    assert isinstance(channel_error, DeribitError)
    assert isinstance(channel_error, ValueError)
    assert isinstance(mapping_error, DeribitError)
    assert isinstance(mapping_error, ValueError)
    assert isinstance(order_not_found_error, DeribitOrderError)
    assert isinstance(order_not_found_error, DeribitNotFoundError)
