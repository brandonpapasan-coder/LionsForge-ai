from app.core.config import Settings
from app.core.legacy_finance_config import LegacyFinanceSettings
from app.core.legacy_market_config import LegacyMarketSettings


LEGACY_MARKET_FIELDS = {
    "market_data_provider",
    "market_data_api_key",
    "market_data_failover_providers",
}


LEGACY_FINANCE_FIELDS = {"enable_legacy_finance_modules"}


def test_active_settings_exclude_legacy_configuration_fields():
    active_fields = set(Settings.model_fields)

    assert not {field for field in active_fields if field.startswith("market_data_")}
    assert "enable_legacy_finance_modules" not in active_fields


def test_legacy_market_settings_own_only_compatibility_provider_fields():
    assert set(LegacyMarketSettings.model_fields) == LEGACY_MARKET_FIELDS


def test_legacy_finance_settings_own_only_compatibility_enablement_field():
    assert set(LegacyFinanceSettings.model_fields) == LEGACY_FINANCE_FIELDS
