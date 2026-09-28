import time
from collections import defaultdict
from threading import Lock
from fastapi import Request, HTTPException, status


class InMemoryRateLimiter:
    """Sliding window in-memory rate limiter per IP address."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self.lock = Lock()

    def check_rate_limit(self, request: Request):
        client_ip = "127.0.0.1"
        if request.client and request.client.host:
            client_ip = request.client.host
        # Also check X-Forwarded-For if behind a proxy
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        now = time.time()
        cutoff = now - self.window_seconds

        with self.lock:
            # Filter out entries older than window
            valid_timestamps = [ts for ts in self.requests[client_ip] if ts > cutoff]
            if len(valid_timestamps) >= self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {self.max_requests} submissions per minute per IP.",
                )
            valid_timestamps.append(now)
            self.requests[client_ip] = valid_timestamps


rate_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60)
