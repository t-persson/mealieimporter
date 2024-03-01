import asyncio
import sys
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Queue, Empty
from typing import Union
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from mealie.utilities.logging import SSEHandler
from mealie.utilities.mealie import Mealie

APP = FastAPI()
RETRY_TIMEOUT = 15000
EXECUTOR = ThreadPoolExecutor()

FRONTEND = Path(__file__).parent.joinpath("frontend")
STATIC = Path(__file__).parent.joinpath("static")
print(STATIC)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)


def import_recipe(api: str, recipe: str, queue: Queue):
    logger = logging.getLogger("SomethingUnique")
    logger.addHandler(SSEHandler(queue))
    mealie = Mealie(logger)
    try:
        mealie.run(api, recipe)
    finally:
        queue.put_nowait("done")


@APP.get("/api")
async def importer(api: str, recipe: str, request: Request):
    message_queue = Queue()
    loop = asyncio.get_event_loop()
    loop.run_in_executor(EXECUTOR, import_recipe, api, recipe, message_queue)
    # loop.create_task(import_recipe(api, recipe, message_queue))
    async def event_generator():
        count = 1
        while True:
            if await request.is_disconnected():
                break
            try:
                message = message_queue.get_nowait()
                if message == "done":
                    yield {
                        "event": "done",
                        "id": count,
                        "data": "Finished",
                    }
                else:
                    yield {
                        "id": count,
                        "retry": RETRY_TIMEOUT,
                        "data": message,
                    }
                    count += 1
            except Empty:
                await asyncio.sleep(1)
    return EventSourceResponse(event_generator())


APP.mount("/static", StaticFiles(directory=STATIC, html=False))
APP.mount("/", StaticFiles(directory=FRONTEND, html=True))
