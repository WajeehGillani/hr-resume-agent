# src/fallbacks.py
from __future__ import annotations
import time
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@dataclass
class CircuitBreaker:
    """
    Simple breaker with CLOSED → OPEN → HALF-OPEN.
    - OPEN after `threshold` consecutive failures.
    - Stay OPEN for `cooldown_s` seconds.
    - In HALF-OPEN, allow one attempt: success -> CLOSED, failure -> OPEN again.
    """
    threshold: int = 3
    cooldown_s: int = 30

    state: str = "CLOSED"          # CLOSED | OPEN | HALF
    failures: int = 0
    open_until: float = 0.0

    def allow(self) -> bool:
        now = time.time()
        if self.state == "OPEN":
            if now >= self.open_until:
                self.state = "HALF"
                return True
            return False
        return True  # CLOSED or HALF

    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"
        self.open_until = 0.0

    def record_failure(self):
        if self.state == "HALF":
            # immediate re-open on failure
            self.state = "OPEN"
            self.open_until = time.time() + self.cooldown_s
            self.failures = self.threshold
            return
        self.failures += 1
        if self.failures >= self.threshold:
            self.state = "OPEN"
            self.open_until = time.time() + self.cooldown_s

# Singleton breaker you can import
breaker = CircuitBreaker()

def retry_policy(attempts: int = 3):
    """Factory: tenacity retry policy with exponential backoff."""
    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(min=1, max=8),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
