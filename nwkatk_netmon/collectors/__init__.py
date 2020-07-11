#     Copyright 2020, Jeremy Schulman
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.


import asyncio
import functools
from base64 import encodebytes

from nwkatk_netmon.log import log

__all__ = ["interval_collector", "b64encodestr"]


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

            log.debug(f"{device.name}: Waiting {interval}s before next collection")
            await asyncio.sleep(interval)
            asyncio.create_task(wrapped(device=device, interval=interval, **kwargs))

        return wrapped

    return decorate


def b64encodestr(str_value):
    return encodebytes(bytes(str_value, encoding="utf-8")).replace(b"\n", b"")
