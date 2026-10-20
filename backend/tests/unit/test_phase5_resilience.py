import pytest
import time
from unittest.mock import MagicMock
from app.pipeline.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpenException
from app.pipeline.stage5_retrieval import FootageRetrievalEngine

class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker("TestProvider", failure_threshold=2)
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_success_maintains_closed(self):
        cb = CircuitBreaker("TestProvider", failure_threshold=2)
        fn = MagicMock(return_value="data")
        res = cb.call(fn)
        assert res == "data"
        assert cb.state == CircuitState.CLOSED
        assert cb.success_count == 1

    def test_trips_to_open_after_threshold(self):
        cb = CircuitBreaker("TestProvider", failure_threshold=2, recovery_timeout_seconds=10.0)
        failing_fn = MagicMock(side_effect=RuntimeError("API down"))

        # First failure
        with pytest.raises(RuntimeError):
            cb.call(failing_fn)
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 1

        # Second failure trips breaker
        with pytest.raises(RuntimeError):
            cb.call(failing_fn)
        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 2

    def test_fast_fail_when_open(self):
        cb = CircuitBreaker("TestProvider", failure_threshold=1, recovery_timeout_seconds=10.0)
        cb.force_open()

        fn = MagicMock()
        with pytest.raises(CircuitBreakerOpenException) as exc_info:
            cb.call(fn)

        assert "TestProvider" in str(exc_info.value)
        fn.assert_not_called()

    def test_recovery_half_open_to_closed(self):
        cb = CircuitBreaker("TestProvider", failure_threshold=1, recovery_timeout_seconds=0.1)
        cb.force_open()

        # Wait for recovery timeout
        time.sleep(0.15)

        success_fn = MagicMock(return_value="recovered")
        res = cb.call(success_fn)
        assert res == "recovered"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

class TestProviderFailover:
    def test_cascading_failover_to_pixabay_and_mock(self, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "FOOTAGE_ADAPTER", "production")
        monkeypatch.setattr(settings, "PEXELS_API_KEY", "mock_pexels_key")
        engine = FootageRetrievalEngine()
        # Force pexels breaker open
        engine.pexels_breaker.force_open()

        warnings = []
        candidates = engine.retrieve_candidates_for_scene(
            query="business partnership",
            count=2,
            warnings_out=warnings,
        )

        assert len(candidates) > 0
        assert any("Pexels circuit breaker is OPEN" in w or "Failing over" in w for w in warnings)

    def test_job_never_crashes_on_all_provider_exhaustion(self):
        engine = FootageRetrievalEngine()
        engine.pexels_breaker.force_open()
        engine.pixabay_breaker.force_open()
        engine.generative_breaker.force_open()
        # Mock provider returning empty
        engine.mock.search_footage = MagicMock(return_value=[])

        warnings = []
        candidates = engine.retrieve_candidates_for_scene(
            query="quantum encryption network",
            count=2,
            warnings_out=warnings,
        )

        assert len(candidates) > 0
        # Should have fallen back to safe title card
        assert candidates[0]["provider"] == "fallback_title_card"
        assert candidates[0]["ai_generated"] is True
        assert any("Emergency fallback card synthesized" in w for w in warnings)
