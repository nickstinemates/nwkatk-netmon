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

# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import Optional, List
from functools import lru_cache

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from lxml.etree import Element

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from nwkatk_netmon.log import log
from nwkatk_netmon import Metric, timestamp_now
from nwkatk_netmon.collectors import CollectorExecutor, b64encodestr
from nwkatk_netmon.drivers.nxapi import Device


from nwkatk_netmon.collectors import ifdom


@ifdom.IFdomCollectorSpec.start.register
async def start(device: Device, starter: CollectorExecutor, config, **kwargs):  # noqa
    log.info(f"{device.name}: Starting Cisco NXAPI Interface DOM collection")
    starter.start(get_dom_metrics, interval=config.interval, device=device)


_METRIC_VALUE_MAP = {
    "voltage": ifdom.IFdomVoltageMetric,
    "tx_pwr": ifdom.IFdomTxPowerMetric,
    "rx_pwr": ifdom.IFdomRxPowerMetric,
    "temperature": ifdom.IFdomTempMetric,
}


_METRIC_STATUS_MAP = {
    "rx_pwr_flag": ifdom.IFdomRxPowerStatusMetric,
    "tx_pwr_flag": ifdom.IFdomTxPowerStatusMetric,
    "volt_flag": ifdom.IFdomVoltageStatusMetric,
    "temp_flag": ifdom.IFdomTempStatusMetric,
}


async def get_dom_metrics(device: Device) -> Optional[List[Metric]]:
    timestamp = timestamp_now()

    log.info(f"{device.name}: Process DOM metrics ts={timestamp}")

    ifs_dom_res, ifs_status_res = await device.nxapi.exec(
        ["show interface transceiver details", "show interface status"]
    )

    # find all interfaces that have a transceiver present, and the transceiver
    # has a temperature value - guard against non-optical transceivers.

    ifs_dom_data = [
        row_to_dict(ele)
        for ele in ifs_dom_res.output.xpath(
            './/ROW_interface[sfp="present" and temperature]'
        )
    ]

    # noinspection PyArgumentList
    def generate_metrics():

        for if_dom_item in ifs_dom_data:
            if_name = if_dom_item["interface"]

            # for the given interface, if it not in a connected state (up), then do not report

            if_status = ifs_status_res.output.xpath(
                f'TABLE_interface/ROW_interface[interface="{if_name}" and state!="disabled"]'
            )

            if not len(if_status):
                continue

            # obtain the interface description value; handle case if there is none configured.

            if_desc = (if_status[0].findtext("name") or "").strip()
            if_media = (if_dom_item["type"] or if_dom_item["partnum"]).strip()

            # all of the metrics will share the same interface tags

            if_tags = {
                "if_name": if_name,
                "if_desc": b64encodestr(if_desc),
                "media": b64encodestr(if_media),
            }

            for nx_field, metric_cls in _METRIC_VALUE_MAP.items():
                if metric_value := if_dom_item.get(nx_field):
                    yield metric_cls(value=metric_value, tags=if_tags, ts=timestamp)

            for nx_field, metric_cls in _METRIC_STATUS_MAP.items():
                if metric_value := if_dom_item.get(nx_field):
                    yield metric_cls(
                        value=from_flag_to_status(metric_value),
                        tags=if_tags,
                        ts=timestamp,
                    )

    return list(generate_metrics())


@lru_cache
def from_flag_to_status(flag):
    """
     ++  high-alarm; +  high-warning; --  low-alarm; -  low-warning
    """
    return {"++": 2, "--": 2, "+": 1, "-": 1}.get(flag.strip(), 0)


def row_to_dict(row: Element):
    return {ele.tag: ele.text for ele in row.iterchildren()}
