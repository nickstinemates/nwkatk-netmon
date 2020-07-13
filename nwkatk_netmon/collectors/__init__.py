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

from typing import Any, Mapping, Optional, Callable, List, Type
import asyncio
import functools
from base64 import encodebytes

from pydantic import dataclasses, PositiveInt, Field, fields, BaseModel

from nwkatk_netmon import Metric
from nwkatk_netmon.log import log
from nwkatk_netmon import consts


__all__ = ["CollectorType", "CollectorConfigModel", "CollectorExecutor", "b64encodestr"]


def b64encodestr(str_value):
    return encodebytes(bytes(str_value, encoding="utf-8")).replace(b"\n", b"")


class CollectorConfigModel(BaseModel):
    """
    The CollectorConfigModel defines the configuraiton options that the
    collector implements.  By default they must all provide the interval option.
    Each CollectorType can subclass the CollectorConfigModel to add additional
    options.
    """

    interval: Optional[PositiveInt]


class CollectorType(object):
    """
    This dataclass is used to define a collector "type" that will be used by
    Developers so that they can implement per-device
    """

    start: Callable
    config: Optional[CollectorConfigModel] = CollectorConfigModel
    metrics: List[Type[Metric]] = None


class CollectorExecutor(object):
    def __init__(self, config):
        self.config = config

    def start(self, coro, interval, device, **kwargs):
        ic = self.interval_executor(interval)(coro)
        task = ic(device, **kwargs)
        asyncio.create_task(task)

    def interval_executor(self, interval):
        """
        This decorator should be used on all interval based collector coroutines
        so that the coroutine is scheduled on the loop on a interval-periodic
        basis.

        Examples
        --------
        When using this decorator you MUST call it, that is with the parenthesis, as shown:

            @interval_collector()
            async def my_collector(device, interval, **kwargs):
                # does the actual work of the collector

        """

        def decorate(coro):
            @functools.wraps(coro)
            async def wrapped(device, **kwargs):

                # await the original collector coroutine to return the collected
                # metrics.

                metrics = await coro(device=device, **kwargs)
                if metrics:
                    exporter = self.config.exporters["circonus"]
                    asyncio.create_task(
                        exporter.export_metrics(device=device, metrics=metrics)
                    )

                # sleep for an interval of time and then create a new task to
                # invoke the wrapped coroutine so that we get the effect of a
                # periodic invocation.

                log.debug(f"{device.name}: Waiting {interval}s before next collection")
                await asyncio.sleep(interval)
                asyncio.create_task(wrapped(device=device, **kwargs))

            return wrapped

        return decorate
