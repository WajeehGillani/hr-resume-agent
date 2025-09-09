import os, sys, time, random
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.abspath("."))

from src.tools.calendar import create_event_or_fallback
from src.fallbacks import breaker

# Dummy insert function: fail twice, then succeed
class FlakyInsert:
    def __init__(self, fails=2):
        self.fails = fails
    def __call__(self, payload):
        if self.fails > 0:
            self.fails -= 1
            raise RuntimeError("Simulated calendar API failure")
        # Simulate success: do nothing
        return {"id": "demo-123"}

start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)

print("=== Test A: disabled (no USE_REAL_CALENDAR) → always ICS ===")
os.environ.pop("USE_REAL_CALENDAR", None)
res = create_event_or_fallback("Interview: Data Analyst", start, duration_min=45, location="Google Meet")
print(res)

print("\n=== Test B: enabled + flaky insert → retries then success, ICS still written ===")
os.environ["USE_REAL_CALENDAR"] = "1"
breaker.state = "CLOSED"; breaker.failures = 0
res = create_event_or_fallback(
    "Interview: Data Analyst",
    start + timedelta(hours=2),
    duration_min=30,
    location="Zoom",
    insert_fn=FlakyInsert(fails=2),  # first two attempts fail, third succeeds
)
print(res)

print("\n=== Test C: breaker OPEN → immediate fallback ===")
# Trip the breaker quickly
breaker.state = "OPEN"; breaker.open_until = time.time() + 60
res = create_event_or_fallback(
    "Interview: Data Analyst",
    start + timedelta(hours=4),
    insert_fn=FlakyInsert(fails=0),
)
print(res)

print("\nDone. Check 'artifacts/invite.ics' exists and inspect it.")