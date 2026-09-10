import time


class Timer:
    def __init__(self):
        self.start = 0.0
        self.elapsed_ms = 0.0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = (time.perf_counter() - self.start) * 1000.0

    async def __aenter__(self):
        self.start = time.perf_counter()
        return self

    async def __aexit__(self, *args):
        self.elapsed_ms = (time.perf_counter() - self.start) * 1000.0
