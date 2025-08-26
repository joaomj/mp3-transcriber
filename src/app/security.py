from slowapi import Limiter
from slowapi.util import get_remote_address

# Limits requests to 10 per minute per IP address to prevent abuse.
limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])
