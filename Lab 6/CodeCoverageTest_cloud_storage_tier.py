
import pytest
from cloud_storage_tier import process_storage_tenants, monitor_replication_latency


def test_invalid_inputs():
    with pytest.raises(ValueError):
        process_storage_tenants("invalid", 10)

    with pytest.raises(ValueError):
        process_storage_tenants([], -1)


def test_inactive_tenant():
    result = process_storage_tenants(
        [{"account_active": False}], 10
    )
    assert result["status"] == "ZERO_USAGE"


def test_all_storage_tiers():
    tenants = [
        {"account_active": True, "tier": "hot",
         "buckets": [{"size_gb": 100, "egress_gb": 50}]},
        {"account_active": True, "tier": "cool",
         "buckets": [{"size_gb": 100, "egress_gb": 50}]},
        {"account_active": True, "tier": "archive",
         "buckets": [{"size_gb": 100, "egress_gb": 50}]}
    ]
    result = process_storage_tenants(tenants, 10)
    assert result["total_billed"] == 4.5
    assert result["status"] == "BILLED"


def test_unknown_tier():
    result = process_storage_tenants(
        [{"account_active": True, "tier": "unknown"}], 10
    )
    assert result["status"] == "ZERO_USAGE"


def test_invalid_bucket_size():
    result = process_storage_tenants(
        [{"account_active": True,
          "buckets": [{"size_gb": 0}]}], 10
    )
    assert result["status"] == "ZERO_USAGE"


def test_corrupted_hot_bucket():
    result = process_storage_tenants(
        [{"account_active": True, "tier": "hot",
          "buckets": [{"size_gb": 100, "corrupted": True}]}], 10
    )
    assert result["status"] == "ZERO_USAGE"


def test_corrupted_archive_bucket():
    result = process_storage_tenants(
        [{"account_active": True, "tier": "archive",
          "buckets": [
              {"size_gb": 100, "corrupted": True},
              {"size_gb": 200}
          ]}], 10
    )
    assert result["status"] == "ZERO_USAGE"


def test_large_bucket_and_egress():
    result = process_storage_tenants(
        [{"account_active": True, "tier": "hot",
          "buckets": [
              {"size_gb": 600, "egress_gb": 150}
          ]}], 10
    )
    assert result["total_billed"] == 17.5


def test_backup_vault():
    result = process_storage_tenants(
        [{"account_active": True, "tier": "hot",
          "has_backup_vault": True,
          "buckets": [{"size_gb": 100}]}], 10
    )
    assert result["total_billed"] == 12.5


def test_audit_flagged():
    result = process_storage_tenants(
        [{"account_active": True, "tier": "hot",
          "buckets": [
              {"size_gb": 0},
              {"size_gb": 0},
              {"size_gb": 0},
              {"size_gb": 0},
              {"size_gb": 0}
          ]}], 10
    )
    assert result["status"] == "AUDIT_FLAGGED"


def test_empty_cluster():
    assert monitor_replication_latency([]) == "NO_DATA"


def test_replication_synced():
    assert monitor_replication_latency(
        [[100, 150, 180], [90, 120]]
    ) == "SYNCED"


def test_replication_lag_alert():
    assert monitor_replication_latency(
        [[250, 300]]
    ) == "SYNC_LAG_ALERT"


def test_replication_lag_reset():
    assert monitor_replication_latency(
        [[250, 100, 250, 300]]
    ) == "SYNC_LAG_ALERT"
