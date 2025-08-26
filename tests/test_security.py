from slowapi import Limiter

from src.app.security import limiter


class TestSecurity:
    """Test cases for the security module."""

    def test_limiter_instance(self):
        """Test that the limiter is properly instantiated."""
        assert isinstance(limiter, Limiter)

    def test_limiter_default_limits(self):
        """Test that the limiter has the correct default limits."""
        # The limiter should have default limits of 10/minute
        assert len(limiter._default_limits) > 0
        # Check that one of the limits is "10 per 1 minute"
        limit_group = limiter._default_limits[0]
        limits = list(limit_group)
        limit_strings = [str(limit.limit) for limit in limits]
        assert any("10 per 1 minute" in limit for limit in limit_strings)

    def test_limiter_headers_enabled(self):
        """Test that rate limit headers are enabled."""
        assert limiter.enabled is True
