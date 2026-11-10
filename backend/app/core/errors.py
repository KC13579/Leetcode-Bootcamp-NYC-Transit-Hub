class APIError(Exception):
    """An expected domain or integration error safe to expose to an API caller."""

    def __init__(self, status_code: int, detail: str):
        """Create an API error with a caller-safe status code and message."""
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)
