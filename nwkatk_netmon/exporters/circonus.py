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

import os
import asyncio
from functools import lru_cache
from itertools import chain

import httpx
from tenacity import retry, wait_exponential

from nwkatk_netmon import Metric
from nwkatk_netmon.log import log

circonus_sem4 = asyncio.Semaphore(100)


@lru_cache()
def circonus_url():
    return os.environ["CIRCONUS_URL"]


def make_circonus_metric(device_tags, metric: Metric):
    all_tags = chain(device_tags.items(), metric.tags.items())

    def to_str(value):
        if isinstance(value, bytes):
            return 'b"%s"' % value.decode("utf-8")
        else:
            return value

    stream_tags = ",".join(f"{key}:{to_str(value)}" for key, value in all_tags)

    name = f"{metric.name}|ST[{stream_tags}]"
    value = metric.value
    return name, value


async def export_metrics(device, metrics):
    log.debug(f"{device.host}: Exporting {len(metrics)} metrics")

    post_url = circonus_url()
    post_data = dict(
        make_circonus_metric(
            device_tags=device.private["tags"],
            metric=metric,
        )
        for metric in metrics
    )

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10))
    async def to_circonus():
        async with httpx.AsyncClient(
            verify=False, headers={"content-type": "application/json"},
        ) as api:
            res = await api.put(post_url, json=post_data)
            log.debug(f"{device.host}: Circonus PUT status {res.status_code}")

    try:
        await to_circonus()
    except httpx.Timeout:
        log.error(f"{device.host}: Unable to send metrics to Circonus due to timeout")
