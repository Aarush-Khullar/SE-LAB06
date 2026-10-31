
import pytest
from cloud_storage_tier import process_storage_tenants, monitor_replication_latency


def test_invalid_tenants():
    with pytest.raises(ValueError):
        process_storage_tenants("invalid", 10)

    with pytest.raises(ValueError):
        process_storage_tenants([], -1)


def test_active_and_inactive_tenants():
    result = process_storage_tenants([
        {"account_active": False},
        {"account_active": True, "tier": "hot",
         "buckets": [{"size_gb": 100}]}
    ], 10)
    assert result["status"] == "BILLED"


def test_all_tiers_and_unknown_tier():
    result = process_storage_tenants([
        {"account_active": True, "tier": "hot",
         "buckets": [{"size_gb": 100}]},
        {"account_active": True, "tier": "cool",
         "buckets": [{"size_gb": 100}]},
        {"account_active": True, "tier": "archive",
         "buckets": [{"size_gb": 100}]},
        {"account_active": True, "tier": "unknown",
         "buckets": [{"size_gb": 100}]}
    ], 10)
    assert result["status"] == "BILLED"


def test_bucket_size_branches():
    result = process_storage_tenants([
        {"account_active": True, "tier": "hot",
         "buckets": [
             {"size_gb": 0},
             {"size_gb": 100},
             {"size_gb": 600}
         ]}
    ], 10)
    assert result["total_billed"] == 16.0


def test_corrupted_bucket_branches():
    result = process_storage_tenants([
        {"account_active": True, "tier": "hot",
         "buckets": [{"size_gb": 100, "corrupted": True}]},
        {"account_active": True, "tier": "archive",
         "buckets": [
             {"size_gb": 100, "corrupted": True},
             {"size_gb": 200}
         ]}
    ], 10)
    assert result["status"] == "ZERO_USAGE"


def test_egress_branches():
    result = process_storage_tenants([
        {"account_active": True, "tier": "hot",
         "buckets": [
             {"size_gb": 100, "egress_gb": 50},
             {"size_gb": 100, "egress_gb": 150}
         ]}
    ], 10)
    assert result["total_billed"] == 9.0


def test_backup_vault_branches():
    result = process_storage_tenants([
        {"account_active": True, "tier": "hot",
         "has_backup_vault": True,
         "buckets": [{"size_gb": 100}]},
        {"account_active": True, "tier": "hot",
         "has_backup_vault": False,
         "buckets": [{"size_gb": 100}]}
    ], 10)
    assert result["total_billed"] == 15.0


def test_zero_usage_and_audit_flagged():
    zero = process_storage_tenants([], 10)
    assert zero["status"] == "ZERO_USAGE"

    audit = process_storage_tenants([
        {"account_active": True, "tier": "hot",
         "buckets": [{"size_gb": 0} for _ in range(5)]}
    ], 10)
    assert audit["status"] == "AUDIT_FLAGGED"


def test_replication_no_data():
    assert monitor_replication_latency([]) == "NO_DATA"


def test_replication_synced_and_reset():
    assert monitor_replication_latency(
        [[250, 100, 250, 100], [100, 150]]
    ) == "SYNCED"


def test_replication_alert():
    assert monitor_replication_latency(
        [[250, 300]]
    ) == "SYNC_LAG_ALERT"
