"""Sprint 1 — HeatmapService unit tests.

Coverage:
  - _build_benchmark_heatmap() shape and value contract
  - _best_slots() / _worst_slots() ordering and size
  - HeatmapService.get_heatmap() — benchmark path (< MIN_DATA_POSTS rows)
  - HeatmapService.get_heatmap() — personal path (>= MIN_DATA_POSTS rows)
  - HeatmapService._build_personal_heatmap() normalisation
  - Edge cases: empty raw data, single row, max-rate == 0, impressions = 0
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.heatmap_service import (
    HeatmapService,
    _DAY_NAMES,
    _GLOBAL_BENCHMARKS,
    _best_slots,
    _build_benchmark_heatmap,
    _worst_slots,
)

# ---------------------------------------------------------------------------
# Pure helper tests — no DB needed
# ---------------------------------------------------------------------------


class TestBuildBenchmarkHeatmap:
    def test_returns_all_seven_days(self):
        heatmap = _build_benchmark_heatmap()
        assert set(heatmap.keys()) == set(_DAY_NAMES)

    def test_values_between_zero_and_one(self):
        heatmap = _build_benchmark_heatmap()
        for day, hours in heatmap.items():
            for hour_str, rate in hours.items():
                assert 0.0 <= rate <= 1.0, f"Out of range at {day}:{hour_str} → {rate}"

    def test_tuesday_has_highest_rate(self):
        """Tue 10am should be peak according to our benchmark data."""
        heatmap = _build_benchmark_heatmap()
        assert "10" in heatmap["tuesday"]
        assert heatmap["tuesday"]["10"] == pytest.approx(0.98, abs=0.01)

    def test_weekend_rates_are_low(self):
        heatmap = _build_benchmark_heatmap()
        for hour_str, rate in heatmap.get("saturday", {}).items():
            assert rate < 0.35, f"Saturday rate too high: {rate}"
        for hour_str, rate in heatmap.get("sunday", {}).items():
            assert rate < 0.25, f"Sunday rate too high: {rate}"

    def test_hours_are_string_keys(self):
        heatmap = _build_benchmark_heatmap()
        for day, hours in heatmap.items():
            for k in hours:
                assert isinstance(k, str), f"Key {k!r} is not a string"


class TestBestWorstSlots:
    def test_best_slots_returns_n_items(self):
        heatmap = _build_benchmark_heatmap()
        result = _best_slots(heatmap, n=5)
        assert len(result) == 5

    def test_best_slots_sorted_descending(self):
        heatmap = _build_benchmark_heatmap()
        result = _best_slots(heatmap, n=10)
        rates = [s["avg_engagement_rate"] for s in result]
        assert rates == sorted(rates, reverse=True)

    def test_worst_slots_sorted_ascending(self):
        heatmap = _build_benchmark_heatmap()
        result = _worst_slots(heatmap, n=3)
        rates = [s["avg_engagement_rate"] for s in result]
        assert rates == sorted(rates)

    def test_best_slots_returns_expected_keys(self):
        heatmap = _build_benchmark_heatmap()
        slot = _best_slots(heatmap, n=1)[0]
        assert "day" in slot
        assert "hour" in slot
        assert "avg_engagement_rate" in slot

    def test_best_slots_fewer_than_n(self):
        """If total slots < n, just return all."""
        tiny_heatmap = {"monday": {"9": 0.5}}
        result = _best_slots(tiny_heatmap, n=100)
        assert len(result) == 1

    def test_empty_heatmap_returns_empty(self):
        result = _best_slots({}, n=5)
        assert result == []
        result = _worst_slots({}, n=3)
        assert result == []


# ---------------------------------------------------------------------------
# HeatmapService — unit tests with mocked DB
# ---------------------------------------------------------------------------


class TestHeatmapServiceGetHeatmap:
    def _make_service(self, raw_rows: list[dict]):
        """Helper: create the service with a mock DB that returns raw_rows."""
        db = AsyncMock()

        # _query_raw returns a list of dicts
        async def _query_raw(user_id, weeks):
            return raw_rows

        service = HeatmapService(db)
        service._query_raw = _query_raw  # replace the real DB method
        return service

    @pytest.mark.asyncio
    async def test_benchmark_path_when_insufficient_data(self):
        """< MIN_DATA_POSTS → use global benchmarks, data_source = 'global_benchmark'."""
        service = self._make_service(raw_rows=[])
        result = await service.get_heatmap(uuid.uuid4(), weeks=8)
        assert result["data_source"] == "global_benchmark"
        assert result["sample_size"] == 0
        assert set(result["heatmap"].keys()) == set(_DAY_NAMES)
        assert len(result["best_slots"]) > 0
        assert len(result["worst_slots"]) > 0

    @pytest.mark.asyncio
    async def test_personal_path_when_sufficient_data(self):
        """≥ MIN_DATA_POSTS → use personal heatmap, data_source = 'personal'."""
        raw_rows = [
            {"dow": 1, "hour": 9, "post_count": 5, "avg_rate": 0.05},
            {"dow": 1, "hour": 10, "post_count": 3, "avg_rate": 0.12},
            {"dow": 3, "hour": 9, "post_count": 4, "avg_rate": 0.08},
            {"dow": 3, "hour": 10, "post_count": 6, "avg_rate": 0.15},
            {"dow": 4, "hour": 8, "post_count": 2, "avg_rate": 0.03},
        ]
        service = self._make_service(raw_rows=raw_rows)
        result = await service.get_heatmap(uuid.uuid4(), weeks=8)
        assert result["data_source"] == "personal"
        assert result["sample_size"] == 5

    @pytest.mark.asyncio
    async def test_personal_heatmap_normalised_to_one(self):
        """Max engagement rate should normalise to exactly 1.0."""
        raw_rows = [
            {"dow": 1, "hour": 10, "post_count": 5, "avg_rate": 0.20},
            {"dow": 3, "hour": 9,  "post_count": 3, "avg_rate": 0.10},
            {"dow": 2, "hour": 11, "post_count": 4, "avg_rate": 0.05},
            {"dow": 0, "hour": 8,  "post_count": 2, "avg_rate": 0.02},
            {"dow": 4, "hour": 9,  "post_count": 6, "avg_rate": 0.15},
        ]
        service = self._make_service(raw_rows=raw_rows)
        result = await service.get_heatmap(uuid.uuid4(), weeks=8)
        # Max is tuesday (dow=1) 10am  → should be 1.0
        assert result["heatmap"]["tuesday"]["10"] == pytest.approx(1.0, abs=0.001)

    @pytest.mark.asyncio
    async def test_all_seven_days_present_in_personal_heatmap(self):
        raw_rows = [
            {"dow": i, "hour": 10, "post_count": 2, "avg_rate": 0.05}
            for i in range(5)  # Only weekdays
        ]
        service = self._make_service(raw_rows=raw_rows)
        result = await service.get_heatmap(uuid.uuid4(), weeks=8)
        # All 7 days must be present (empty for missing ones)
        assert set(result["heatmap"].keys()) == set(_DAY_NAMES)

    @pytest.mark.asyncio
    async def test_benchmark_has_four_rows_still_uses_benchmarks(self):
        """4 rows < MIN_DATA_POSTS (5) → still benchmark."""
        raw_rows = [
            {"dow": 1, "hour": 9, "post_count": 1, "avg_rate": 0.1},
            {"dow": 2, "hour": 10, "post_count": 1, "avg_rate": 0.2},
            {"dow": 3, "hour": 9, "post_count": 1, "avg_rate": 0.15},
            {"dow": 4, "hour": 8, "post_count": 1, "avg_rate": 0.05},
        ]
        service = self._make_service(raw_rows=raw_rows)
        result = await service.get_heatmap(uuid.uuid4(), weeks=8)
        assert result["data_source"] == "global_benchmark"

    @pytest.mark.asyncio
    async def test_response_structure_has_required_keys(self):
        service = self._make_service(raw_rows=[])
        result = await service.get_heatmap(uuid.uuid4())
        assert "heatmap" in result
        assert "best_slots" in result
        assert "worst_slots" in result
        assert "data_source" in result
        assert "sample_size" in result


class TestBuildPersonalHeatmap:
    """Unit tests for the private _build_personal_heatmap method."""

    def _make_service(self):
        db = AsyncMock()
        return HeatmapService(db)

    def test_empty_raw_returns_empty_days(self):
        service = self._make_service()
        result = service._build_personal_heatmap([])
        assert all(v == {} for v in result.values())

    def test_max_rate_zero_does_not_divide_by_zero(self):
        """avg_rate = 0 for all rows — max_rate clamps to 1.0 to avoid ZeroDivisionError."""
        raw = [{"dow": 0, "hour": 9, "post_count": 2, "avg_rate": 0.0}]
        service = self._make_service()
        result = service._build_personal_heatmap(raw)
        assert result["monday"]["9"] == pytest.approx(0.0, abs=0.001)

    def test_normalised_values_are_0_to_1(self):
        raw = [
            {"dow": 1, "hour": 9, "post_count": 5, "avg_rate": 0.10},
            {"dow": 1, "hour": 10, "post_count": 3, "avg_rate": 0.50},
            {"dow": 3, "hour": 8, "post_count": 2, "avg_rate": 0.25},
        ]
        service = self._make_service()
        result = service._build_personal_heatmap(raw)
        for day, hours in result.items():
            for hour_str, rate in hours.items():
                assert 0.0 <= rate <= 1.0, f"Out of range: {day}:{hour_str}={rate}"
