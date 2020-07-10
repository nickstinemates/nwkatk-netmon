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
from asynceapi import Device

from nwkatk_netmon import timestamp_now
from nwkatk_netmon.collectors import interval_collector, b64encodestr
from nwkatk_netmon.collectors import ifdom
from nwkatk_netmon.exporters.circonus import export_metrics
from nwkatk_netmon.log import log


@ifdom.ifdom_start.register
async def start(device: Device, interval, **kwargs):
    log.info(f"{device.host}: Connecting to EOS device")

    try:
        res = await device.exec(["show hostname"])
    except Exception as exc:
        log.error(f"{device.host} No API access: {str(exc)}, skipping.")
        return

    device.host = res[0].output["hostname"]
    log.info(f"{device.host}: Starting Interface DOM collection")
    asyncio.create_task(get_dom_metrics(device, interval=interval, **kwargs))


@interval_collector()
async def get_dom_metrics(device: Device, interval: int, **kwargs):  # noqa
    log.debug(f"{device.host}: Getting DOM information")

    if_dom_res, if_desc_res = await device.exec(
        ["show interfaces transceiver detail", "show interfaces description"]
    )

    if not if_dom_res.ok:
        log.error(
            f"{device.host}: failed to collect DOM information: {if_dom_res.output}, aborting device."
        )
        return

    # both ifs_desc and ifs_dom are dict[<if_name>]

    ifs_desc = if_desc_res.output["interfaceDescriptions"]
    ifs_dom = if_dom_res.output["interfaces"]

    def ok_process_if(if_name):

        # if the interface name does not exist in the interface description data it likely means that the interface name
        # is an unused transciever lane; and if so then it would be the same data as the "first lane".  In this case we
        # don't need to record a duplicate metric.

        if not (if_desc := ifs_desc.get(if_name)):
            return False

        # do not report on interfaces that are administratively disabled.

        if if_desc["interfaceStatus"] == "adminDown":
            return False

        return True

    if_metrics = [
        measurement
        for if_name, if_dom_data in ifs_dom.items()
        if if_dom_data and ok_process_if(if_name)
        for measurement in make_if_metrics(
            if_name, if_dom_data, if_desc=ifs_desc[if_name]["description"]
        )
    ]

    if if_metrics:
        asyncio.create_task(
            export_metrics(device=device, metrics=if_metrics)
        )


def make_if_metrics(if_name, if_dom_data, if_desc):
    ts = timestamp_now()

    c_tags = {
        "if_name": if_name,
        "if_desc": b64encodestr(if_desc),
        "media": b64encodestr(if_dom_data["mediaType"]),
    }

    m_txpow = ifdom.IFdomTxPowerMetric(value=if_dom_data["txPower"], tags=c_tags, ts=ts)
    m_rxpow = ifdom.IFdomRxPowerMetric(value=if_dom_data["rxPower"], tags=c_tags, ts=ts)
    m_temp = ifdom.IFdomTempMetric(value=if_dom_data["temperature"], tags=c_tags, ts=ts)
    m_volt = ifdom.IFdomVoltageMetric(value=if_dom_data["voltage"], tags=c_tags, ts=ts)

    yield from [m_txpow, m_rxpow, m_temp, m_volt]

    thresholds = if_dom_data["details"]

    yield ifdom.IFdomRxPowerStatusMetric(
        value=threshold_outside(value=m_rxpow.value, thresholds=thresholds["rxPower"]),
        tags=c_tags, ts=ts
    )

    yield ifdom.IFdomTxPowerStatusMetric(
        value=threshold_outside(value=m_txpow.value, thresholds=thresholds["txPower"]),
        tags=c_tags, ts=ts
    )

    yield ifdom.IFdomTempStatusMetric(
        value=threshold_outside(value=m_temp.value, thresholds=thresholds["temperature"]),
        tags=c_tags, ts=ts
    )

    yield ifdom.IFdomVoltageStatusMetric(
        value=threshold_outside(value=m_volt.value, thresholds=thresholds["voltage"]),
        tags=c_tags, ts=ts
    )


def threshold_outside(value, thresholds):
    if value <= thresholds["lowAlarm"] or value >= thresholds["highAlarm"]:
        return 2

    if value <= thresholds["lowWarn"] or value >= thresholds["highWarn"]:
        return 1

    return 0
