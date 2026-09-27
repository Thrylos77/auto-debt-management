"""Centralized conversion between API values and stored text values."""

import json
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse


class ConfigurationTypeCodec:
    """Encode and decode supported configuration value types."""

    DURATION_PATTERN = re.compile(r"^(?P<amount>\d+)(?P<unit>[smhd])$")

    @classmethod
    def decode(cls, raw_value: str, value_type: str):
        """Convert a stored string into the configured Python representation."""

        if value_type == "STRING":
            return raw_value

        if value_type == "INTEGER":
            try:
                return int(raw_value)
            except (TypeError, ValueError) as exc:
                raise ValueError("Invalid INTEGER configuration value.") from exc

        if value_type == "BOOLEAN":
            normalized = str(raw_value).strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
            raise ValueError("Invalid BOOLEAN configuration value.")

        if value_type == "DECIMAL":
            try:
                return Decimal(raw_value)
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise ValueError("Invalid DECIMAL configuration value.") from exc

        if value_type == "JSON":
            try:
                return json.loads(raw_value)
            except (TypeError, json.JSONDecodeError) as exc:
                raise ValueError("Invalid JSON configuration value.") from exc

        if value_type == "URL":
            parsed = urlparse(str(raw_value))
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL configuration value.")
            return str(raw_value)

        if value_type == "DURATION":
            try:
                return int(raw_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "DURATION values are stored as integer seconds."
                ) from exc

        raise ValueError(f"Unsupported configuration type: {value_type}")

    @classmethod
    def encode(cls, value, value_type: str) -> str:
        """Validate and convert an API value into database text."""

        if value_type == "STRING":
            return str(value)

        if value_type == "INTEGER":
            try:
                return str(int(value))
            except (TypeError, ValueError) as exc:
                raise ValueError("Invalid INTEGER configuration value.") from exc

        if value_type == "BOOLEAN":
            if isinstance(value, bool):
                return "true" if value else "false"
            normalized = str(value).strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return "true"
            if normalized in {"false", "0", "no", "off"}:
                return "false"
            raise ValueError("Invalid BOOLEAN configuration value.")

        if value_type == "DECIMAL":
            try:
                return str(Decimal(str(value)))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise ValueError("Invalid DECIMAL configuration value.") from exc

        if value_type == "JSON":
            try:
                return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            except (TypeError, ValueError) as exc:
                raise ValueError("Invalid JSON configuration value.") from exc

        if value_type == "URL":
            cls.decode(str(value), "URL")
            return str(value)

        if value_type == "DURATION":
            if isinstance(value, int) and value >= 0:
                return str(value)
            if isinstance(value, str):
                match = cls.DURATION_PATTERN.fullmatch(value.strip().lower())
                if match:
                    amount = int(match.group("amount"))
                    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
                    return str(amount * multipliers[match.group("unit")])
            raise ValueError(
                "DURATION values must be integer seconds or use a suffix "
                "such as 30m, 2h or 7d."
            )

        raise ValueError(f"Unsupported configuration type: {value_type}")
