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
"""
This file contains the Interface DOM metrics collector supporing the Cisco NXAPI
enabled devices.
"""

# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import Optional, List
from functools import lru_cache

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from lxml.etree import Element

from nwkatk_netmon.log import log
from nwkatk_netmon import Metric, timestamp_now, b64encodestr
from nwkatk_netmon.collectors import CollectorExecutor
from nwkatk_netmon.drivers.nxapi import Device

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from nwkatk_netmon.collectors import ifdom

# no exports

__all__ = []


@ifdom.register
async def start(device: Device, executor: CollectorExecutor, config):
    """
    The IF DOM collector start coroutine for Cisco NX-API enabled devices.  The
    purpose of this coroutine is to start the collector task.  Nothing fancy.

    Parameters
    ----------
    device:
        The device driver instance for the Cisco device

    executor:
        The netmon executor that is used to start one or more collector tasks.
        In this instance, there is only one collector task started per device.

    config:
        The IF DOM collector config.  Currently there the IF DOM collector does
        not provide any additional configuration options.
    """
    log.info(f"{device.name}: Starting Cisco NXAPI Interface DOM collection")
    executor.start(get_dom_metrics, interval=config.interval, device=device)


async def get_dom_metrics(device: Device) -> Optional[List[Metric]]:
    """
    This coroutine will be executed as a asyncio Task on a periodic basis, the
    purpose is to collect data from the device and return the list of Interface
    DOM metrics.

    Parameters
    ----------
    device:
        The Cisco device driver instance for this device.

    Returns
    -------
    Option list of Metic items.
    """
    timestamp = timestamp_now()

    log.info(f"{device.name}: Process DOM metrics ts={timestamp}")

    ifs_dom_res, ifs_status_res = await device.nxapi.exec(
        ["show interface transceiver details", "show interface status"]
    )

    # find all interfaces that have a transceiver present, and the transceiver
    # has a temperature value - guard against non-optical transceivers.

    ifs_dom_data = [
        _row_to_dict(ele)
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
                        value=_from_flag_to_status(metric_value),
                        tags=if_tags,
                        ts=timestamp,
                    )

    return list(generate_metrics())


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


@lru_cache
def _from_flag_to_status(flag: str) -> int:
    """
    The Cisco NX-OS system performs the computation to determine if a value exceeds
    the DOM threshold.  This funciton maps the Cisco provided flag value into the
    status value (0=ok, 1=warn, 2=alert)

    Flags are:
        ++  high-alarm
        --  low-alarm
        +  high-warning
        -  low-warning
    """
    return {"++": 2, "--": 2, "+": 1, "-": 1}.get(flag.strip(), 0)


def _row_to_dict(row: Element):
    """ helper function to convert XML elements into a dict obj. """
    return {ele.tag: ele.text for ele in row.iterchildren()}
