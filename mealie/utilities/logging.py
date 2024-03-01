import logging
from queue import Queue

class SSEHandler(logging.StreamHandler):
    def __init__(self, queue: Queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = queue

    def emit(self, record):
        msg = self.format(record)
        self.queue.put_nowait(f"{record.levelname}: {msg}")
