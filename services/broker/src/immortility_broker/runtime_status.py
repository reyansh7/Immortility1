"""Read-only change notification; Engine/Store still owns all durable task state."""

import asyncio


class RuntimeChanges:
    def __init__(self) -> None:
        self.revision = 0
        self.changed = asyncio.Event()

    def notify(self) -> None:
        self.revision += 1
        previous, self.changed = self.changed, asyncio.Event()
        previous.set()

    async def wait(self, after: int | None, timeout: float = 20) -> None:
        if after is None or after != self.revision:
            return
        event = self.changed
        try:
            await asyncio.wait_for(event.wait(), timeout)
        except TimeoutError:
            pass
