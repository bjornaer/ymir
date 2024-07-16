import asyncio
from typing import Any, Callable, Coroutine, Dict


class AsyncSupport:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.coroutine_map: Dict[str, Callable[..., Coroutine]] = {}

    def register_coroutine(self, name: str, coro: Callable[..., Coroutine]) -> None:
        self.coroutine_map[name] = coro

    def run_coroutine(self, name: str, *args: Any) -> Any:
        if name not in self.coroutine_map:
            raise NameError(f"Coroutine {name} not found")
        return self.loop.run_until_complete(self.coroutine_map[name](*args))

    def create_coroutine(self, func: Callable[..., Any], *args: Any) -> Coroutine:
        async def coro():
            await asyncio.sleep(0)  # Yield control to simulate async behavior
            return func(*args)

        return coro

    def await_coroutine(self, coro: Coroutine) -> Any:
        return self.loop.run_until_complete(coro)
