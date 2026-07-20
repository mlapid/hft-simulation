from collections.abc import Mapping
from typing import Any


class DeribitError(Exception):
    '''
    Base class for all Deribit adapter errors.
    '''


class DeribitRpcError(DeribitError):
    '''
    Error returned by Deribit for a JSON-RPC request.
    '''

    def __init__(self, code: int | None, message: str, data: Any | None = None):
        self.code = code
        self.message = message
        self.data = data

        if code is None:
            detail = f'Deribit RPC error: {message}'
        else:
            detail = f'Deribit RPC error {code}: {message}'

        super().__init__(detail)

    @classmethod
    def from_error(cls, error: Mapping[str, Any]) -> 'DeribitRpcError':
        '''
        Build the most specific known Deribit RPC exception for an error object.
        '''

        code = error.get('code')
        if type(code) is not int:
            code = None

        message = error.get('message')
        if not isinstance(message, str) or not message:
            message = 'Unknown Deribit RPC error'

        error_type = cls._specific_error_type(code=code, message=message)

        return error_type(
            code=code,
            message=message,
            data=error.get('data')
        )

    @classmethod
    def _specific_error_type(
        cls,
        *,
        code: int | None,
        message: str,
    ) -> type['DeribitRpcError']:
        return (
            DERIBIT_RPC_ERROR_MESSAGES.get(message)
            or (DERIBIT_RPC_ERROR_CODES.get(code) if code is not None else None)
            or cls
        )


class DeribitAdapterError(Exception):
    '''
    Base class for all Deribit adapter errors.
    '''


class DeribitAuthenticationError(DeribitRpcError):
    '''
    Error raised when Deribit rejects authentication or authorization.
    '''


class DeribitAuthorizationRequiredError(DeribitAuthenticationError):
    '''
    Error raised when Deribit requires authentication for the request.
    '''


class DeribitInvalidCredentialsError(DeribitAuthenticationError):
    '''
    Error raised when Deribit rejects credentials.
    '''


class DeribitUnauthorizedError(DeribitAuthenticationError):
    '''
    Error raised when Deribit rejects or expires an authorization token.
    '''


class DeribitPermissionDeniedError(DeribitAuthenticationError):
    '''
    Error raised when Deribit denies permission for the request.
    '''


class DeribitInsufficientFundsError(DeribitRpcError):
    '''
    Error raised when Deribit reports insufficient funds.
    '''


class DeribitRateLimitError(DeribitRpcError):
    '''
    Error raised when Deribit rate-limits a request.
    '''


class DeribitNotFoundError(DeribitRpcError):
    '''
    Error raised when Deribit cannot find the requested resource.
    '''


class DeribitOrderError(DeribitRpcError):
    '''
    Error raised when Deribit rejects an order operation.
    '''


class DeribitOrderNotFoundError(DeribitOrderError, DeribitNotFoundError):
    '''
    Error raised when Deribit cannot find the requested order.
    '''


class DeribitPostOnlyRejectError(DeribitOrderError):
    '''
    Error raised when Deribit rejects a post-only order.
    '''


class DeribitInvalidArgumentError(DeribitRpcError):
    '''
    Error raised when Deribit rejects request arguments.
    '''


class DeribitInvalidInstrumentError(DeribitInvalidArgumentError):
    '''
    Error raised when Deribit rejects an instrument name.
    '''


class DeribitRetryableError(DeribitRpcError):
    '''
    Error raised when Deribit signals that the request can be retried.
    '''


class DeribitSystemMaintenanceError(DeribitRetryableError):
    '''
    Error raised when Deribit reports system maintenance.
    '''


class DeribitJsonRpcProtocolError(DeribitRpcError):
    '''
    Error raised for JSON-RPC protocol-level failures.
    '''


class DeribitInvalidParamsError(DeribitJsonRpcProtocolError):
    '''
    Error raised when Deribit reports invalid JSON-RPC parameters.
    '''


class DeribitMethodNotFoundError(DeribitJsonRpcProtocolError):
    '''
    Error raised when Deribit reports an unknown JSON-RPC method.
    '''


class DeribitParseError(DeribitJsonRpcProtocolError):
    '''
    Error raised when Deribit cannot parse a JSON-RPC request.
    '''


class DeribitMissingParamsError(DeribitJsonRpcProtocolError):
    '''
    Error raised when Deribit reports missing JSON-RPC parameters.
    '''


class DeribitPayloadTooLargeError(DeribitJsonRpcProtocolError):
    '''
    Error raised when Deribit rejects an oversized request payload.
    '''


class DeribitConnectionError(ConnectionError, DeribitError):
    '''
    Error raised when a connection to Deribit fails.
    '''


class DeribitChannelError(ValueError, DeribitError):
    '''
    Error raised when a Deribit channel cannot be built from the provided options.
    '''


class DeribitSubscriptionError(DeribitError):
    '''
    Error raised when a Deribit subscription response or notification is invalid.
    '''


class DeribitMappingError(ValueError, DeribitError):
    '''
    Error raised when a Deribit payload cannot be mapped safely.
    '''


DERIBIT_RPC_ERROR_MESSAGES: dict[str, type[DeribitRpcError]] = {
    'authorization_required': DeribitAuthorizationRequiredError,
    'invalid_credentials': DeribitInvalidCredentialsError,
    'invalid_token': DeribitUnauthorizedError,
    'unauthorized': DeribitUnauthorizedError,
    'insufficient_scope': DeribitPermissionDeniedError,
    'scope_exceeded': DeribitPermissionDeniedError,
    'forbidden': DeribitPermissionDeniedError,
    'permission_denied': DeribitPermissionDeniedError,
    'not_enough_funds': DeribitInsufficientFundsError,
    'insufficient_funds': DeribitInsufficientFundsError,
    'too_many_requests': DeribitRateLimitError,
    'too_many_concurrent_requests': DeribitRateLimitError,
    'not_found': DeribitNotFoundError,
    'order_not_found': DeribitOrderNotFoundError,
    'post_only_reject': DeribitPostOnlyRejectError,
    'invalid_argument': DeribitInvalidArgumentError,
    'invalid_arguments': DeribitInvalidArgumentError,
    'bad_argument': DeribitInvalidArgumentError,
    'bad_arguments': DeribitInvalidArgumentError,
    'invalid_or_unsupported_instrument': DeribitInvalidInstrumentError,
    'retry': DeribitRetryableError,
    'temporarily_unavailable': DeribitRetryableError,
    'timed_out': DeribitRetryableError,
    'system_maintenance': DeribitSystemMaintenanceError,
    'Invalid params': DeribitInvalidParamsError,
    'Method not found': DeribitMethodNotFoundError,
    'Parse error': DeribitParseError,
    'Missing params': DeribitMissingParamsError,
    'request entity too large': DeribitPayloadTooLargeError,
}

DERIBIT_RPC_ERROR_CODES: dict[int, type[DeribitRpcError]] = {
    10000: DeribitAuthorizationRequiredError,
    10028: DeribitRateLimitError,
    10066: DeribitRateLimitError,
    11051: DeribitSystemMaintenanceError,
    13004: DeribitInvalidCredentialsError,
    13009: DeribitUnauthorizedError,
    13021: DeribitPermissionDeniedError,
    13028: DeribitRetryableError,
    13403: DeribitPermissionDeniedError,
    13888: DeribitRetryableError,
    -32700: DeribitParseError,
    -32602: DeribitInvalidParamsError,
    -32601: DeribitMethodNotFoundError,
    -32600: DeribitPayloadTooLargeError,
    -32000: DeribitMissingParamsError,
}
