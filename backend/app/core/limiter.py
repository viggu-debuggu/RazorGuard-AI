from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared rate limiter instance using remote IP address as the key
limiter = Limiter(key_func=get_remote_address)
