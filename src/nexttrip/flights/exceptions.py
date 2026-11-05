class FlightSearchError(Exception):
    """航空券検索の基底エラー。"""


class FlightSearchConfigError(FlightSearchError):
    """必須の環境変数が不足している場合。"""


class FlightSearchAuthError(FlightSearchError):
    """認証に失敗した場合。"""


class FlightSearchApiError(FlightSearchError):
    """Travelport API が HTTP エラーを返した場合。"""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class FlightSearchTransportError(FlightSearchError):
    """タイムアウト・通信失敗。"""
