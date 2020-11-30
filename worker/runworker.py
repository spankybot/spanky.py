import asyncio
import SpankyWorker


loop = asyncio.get_event_loop()
loop.set_debug(True)

worker = SpankyWorker.PythonWorker()
worker.connect()
worker.run()
