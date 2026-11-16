"""Our own error types. Clients and the service raise them; main.py turns them into HTTP responses."""


class NotFoundError(Exception):
    """Something we asked an outside API about does not exist."""


class CountryNotFoundError(NotFoundError):
    """The country does not exist."""


class UpstreamError(Exception):
    """An outside API is down, too slow, or returned something unusable."""