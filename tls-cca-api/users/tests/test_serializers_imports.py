"""Regression tests for serializer module imports."""


def test_historical_user_serializer_module_imports():
    """The historical serializer must import with its schema decorator available."""
    from users.serializers.users import HistoricalUserSerializer

    assert HistoricalUserSerializer is not None
