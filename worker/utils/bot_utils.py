import threading
import asyncio

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