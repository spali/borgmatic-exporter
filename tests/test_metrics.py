import json
import os

import arrow
import pytest
from prometheus_client import CollectorRegistry

from src import metrics

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


class TestMetrics:
    @pytest.fixture(scope="function")
    def registry(self):
        registry = CollectorRegistry(auto_describe=True)
        yield registry

    @pytest.fixture(scope="function")
    def collect(self, mocker, registry):
        with open(f"{PROJECT_ROOT}/data/repo-info.json") as j:
            ri = json.load(j)

        with open(f"{PROJECT_ROOT}/data/list-info.json") as j:
            li = json.load(j)

        mocker.patch("src.metrics.run_command", side_effect=[ri, li])

        metrics.create_metrics(registry=registry)
        metrics.collect(
            borgmatic_configs=["/conf/foo.yaml", "/conf/bar.yaml", "/conf/baz.yaml"],
            registry=registry,
        )
        yield registry

    def test_run_command(self):
        result = metrics.run_command(command='echo {"foo": "bar"}{"foo2": "bar2"}')
        assert result == [{"foo": "bar"}, {"foo2": "bar2"}]

    def test_run_command_ignore_invalid_json(self):
        result = metrics.run_command(command='echo {"foo": "bar"}{"foo2": ')
        assert result == [{"foo": "bar"}]

    def test_registry(self, registry):
        result = metrics.create_metrics(registry=registry)._names_to_collectors
        assert "borg_total_backups" in result
        assert "borg_total_chunks" in result
        assert "borg_total_compressed_size" in result
        assert "borg_total_size" in result
        assert "borg_total_deduplicated_compressed_size" in result
        assert "borg_total_deduplicated_size" in result
        assert "borg_last_backup_timestamp" in result
        assert "borg_last_backup_duration" in result
        assert "borg_last_backup_files" in result
        assert "borg_last_backup_deduplicated_compressed_size" in result
        assert "borg_last_backup_compressed_size" in result
        assert "borg_last_backup_size" in result

    @pytest.mark.parametrize(
        "metric, repo, expect",
        [
            ("borg_total_backups", "/borg/backup-1", 2.0),
            ("borg_total_backups", "/borg/backup-3", 0.0),
            ("borg_total_chunks", "/borg/backup-1", 3505.0),
            ("borg_total_compressed_size", "/borg/backup-1", 3965903861.0),
            ("borg_total_size", "/borg/backup-1", 8446787072.0),
            ("borg_total_deduplicated_compressed_size", "/borg/backup-1", 537932015.0),
            ("borg_total_deduplicated_size", "/borg/backup-1", 1296544339.0),
            ("borg_total_deduplicated_size", "/borg/backup-2", 21296544339.0),
            ("borg_last_backup_duration", "/borg/backup-1", 107.499993),
            ("borg_last_backup_duration", "/borg/backup-2", 117.189547),
            ("borg_last_backup_files", "/borg/backup-1", 11),
            ("borg_last_backup_files", "/borg/backup-2", 12),
            (
                "borg_last_backup_deduplicated_compressed_size",
                "/borg/backup-1",
                10351331,
            ),
            (
                "borg_last_backup_deduplicated_compressed_size",
                "/borg/backup-2",
                18718565,
            ),
            ("borg_last_backup_compressed_size", "/borg/backup-1", 379050627),
            ("borg_last_backup_compressed_size", "/borg/backup-2", 419966002),
            ("borg_last_backup_size", "/borg/backup-1", 807712494),
            ("borg_last_backup_size", "/borg/backup-2", 893501335),
        ],
    )
    def test_individual_metrics(self, collect, metric, repo, expect):
        registry = collect
        actual = registry.get_sample_value(name=metric, labels={"repository": repo})
        assert actual == expect

    def test_timestamp_metrics(self, collect):
        registry = collect
        actual = registry.get_sample_value(
            name="borg_last_backup_timestamp", labels={"repository": "/borg/backup-1"}
        )
        assert arrow.get(actual)
