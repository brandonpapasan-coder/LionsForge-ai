from app.core.config import Settings
from app.core.legacy_market_config import LegacyMarketSettings


LEGACY_MARKET_FIELDS = {
    "market_data_provider",
    "market_data_api_key",
    "market_data_failover_providers",
}


def test_active_settings_exclude_legacy_market_data_fields():
    active_fields = set(Settings.model_fields)

    assert not {field for field in active_fields if field.startswith("market_data_")}


def test_legacy_market_settings_own_only_compatibility_provider_fields():
    assert set(LegacyMarketSettings.model_fields) == LEGACY_MARKET_FIELDS
