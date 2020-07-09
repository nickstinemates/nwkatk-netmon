import os
import asyncio
from functools import lru_cache
from itertools import chain

import httpx
from tenacity import retry, wait_exponential

from nwkatk_netmon.collectors import Metric
from nwkatk_netmon.log import log

circonus_sem4 = asyncio.Semaphore(100)


@lru_cache()
def circonus_url():
    return os.environ["CIRCONUS_URL"]


def make_circonus_metric(device_tags, metric_prefix: str, metric: Metric):
    all_tags = chain(device_tags.items(), metric.tags.items())

    def to_str(value):
        if isinstance(value, bytes):
            return 'b"%s"' % value.decode("utf-8")
        else:
            return value

    stream_tags = ",".join(f"{key}:{to_str(value)}" for key, value in all_tags)

    name = f"{metric_prefix}_{metric.name}|ST[{stream_tags}]"
    value = metric.value
    return name, value


async def export_metrics(device, metric_prefix, metrics):
    log.debug(f"{device.host}: Exporting {len(metrics)} {metric_prefix} metrics")

    post_url = circonus_url()
    post_data = dict(
        make_circonus_metric(
            device_tags=device.private["tags"],
            metric_prefix=metric_prefix,
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
