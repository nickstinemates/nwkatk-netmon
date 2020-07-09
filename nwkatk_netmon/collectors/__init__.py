import asyncio
import functools
from collections import namedtuple
from base64 import encodebytes

from nwkatk_netmon.log import log

__all__ = ["Metric", "interval_collector", "b64encodestr"]


Metric = namedtuple("Metric", ["name", "value", "tags"])


def interval_collector():
    """
    This decorator should be used on all interval based collector coroutines so that the coroutine is scheduled on the
    loop on a interval-periodic basis.

    Examples
    --------
    When using this decorator you MUST call it, that is with the parenthesis, as shown:

        @interval_collector()
        async def my_collector(device, interval, **kwargs):
            # does the actual work of the collector

    """

    def decorate(coro):
        @functools.wraps(coro)
        async def wrapped(device, interval, **kwargs):
            # await the original collector coroutine

            await coro(device=device, interval=interval, **kwargs)

            # sleep for an interval of time and then create a new task to invoke the wrapped coroutine so that we get
            # the effect of a periodic invocation.

            log.debug(f"{device.host}: Waiting {interval}s before next collection")
            await asyncio.sleep(interval)
            asyncio.create_task(wrapped(device=device, interval=interval, **kwargs))

        return wrapped

    return decorate


# def dead():
# async def next_interval():
#     log.info(f"{hostname}: Waiting {interval}s before next collection")
#     await asyncio.sleep(interval)
#     asyncio.create_task(get_dom_metrics(device, interval))
#
# asyncio.create_task(next_interval())

# option-A
# next_collect = asyncio.create_task(asyncio.sleep(interval))
# next_collect.add_done_callback(lambda _fut: asyncio.create_task(get_dom_metrics(device, interval)))

# option-B
# await asyncio.sleep(collect_interval)
# asyncio.create_task(get_dom_metrics(device, interval))


def b64encodestr(str_value):
    return encodebytes(bytes(str_value, encoding="utf-8")).replace(b"\n", b"")
