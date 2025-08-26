from slowapi import Limiter
from slowapi.util import get_remote_address

# Limits requests to 10 per minute per IP address to prevent abuse.
# This helps protect the service from being overwhelmed by too many requests.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["10/minute"],
    headers_enabled=True,  # Enable rate limit headers in responses
)
