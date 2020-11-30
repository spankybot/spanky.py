import threading
import asyncio

loop = asyncio.get_event_loop()


def run_in_thread(target, args=()):
    """
    Run a function in a thread
    """
    if asyncio.iscoroutinefunction(target):
        thread = threading.Thread(target=asyncio.run, args=(target(*args),))
        thread.start()
    else:
        thread = threading.Thread(target=target, args=args)
        thread.start()

    return thread


async def _wrapped_async(target, args, kwargs):
    try:
        return await target(*args, **kwargs)
    except:
        import traceback

        traceback.print_exc()


def run_async(target, args=(), kwargs={}):
    """
    Runs target in as a threadsafe call
    """
    asyncio.run_coroutine_threadsafe(_wrapped_async(target, args, kwargs), loop)


def run_async_wait(target, args=(), kwargs={}):
    """
    Runs target in as a threadsafe call and returns result
    """
    future = asyncio.run_coroutine_threadsafe(
        _wrapped_async(target, args, kwargs), loop
    )

    return future.result()