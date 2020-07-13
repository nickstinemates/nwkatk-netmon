#  Copyright 2020, Jeremy Schulman
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""
This file contains the Interface DOM metrics collector supporing the Arista EOS
devices.
"""

# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import Optional, List

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from nwkatk_netmon import timestamp_now, Metric
from nwkatk_netmon.collectors import (
    CollectorExecutor,
    b64encodestr,
    CollectorConfigModel,
)
from nwkatk_netmon.log import log
from nwkatk_netmon.drivers.eapi import Device

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from nwkatk_netmon.collectors import ifdom

# no exports
__all__ = []


@ifdom.register
async def start(
    device: Device, executor: CollectorExecutor, config: CollectorConfigModel
):
    """
    The IF DOM collector start coroutine for Arista EOS devices.  The purpose of this
    coroutine is to start the collector task.  Nothing fancy.

    Parameters
    ----------
    device:
        The device driver instance for the Arista device

    executor:
        The netmon executor that is used to start one or more collector tasks.
        In this instance, there is only one collector task started per device.

    config:
        The IF DOM collector config.  Currently there the IF DOM collector does
        not provide any additional configuration options.
    """
    log.info(f"{device.name}: Starting Arista EOS Interface DOM collection")
    executor.start(get_dom_metrics, interval=config.interval, device=device)


async def get_dom_metrics(device: Device) -> Optional[List[Metric]]:
    """
    This coroutine will be executed as a asyncio Task on a periodic basis, the
    purpose is to collect data from the device and return the list of Interface
    DOM metrics.

    Parameters
    ----------
    device:
        The Arisa EOS device driver instance for this device.

    Returns
    -------
    Option list of Metic items.
    """
    log.debug(f"{device.name}: Getting DOM information")

    # Execute the required "show" commands to colelct the interface information
    # needed to produce the Metrics

    if_dom_res, if_desc_res = await device.eapi.exec(
        ["show interfaces transceiver detail", "show interfaces description"]
    )

    if not if_dom_res.ok:
        log.error(
            f"{device.name}: failed to collect DOM information: {if_dom_res.output}, aborting."
        )
        return

    # both ifs_desc and ifs_dom are dict[<if_name>]

    ifs_desc = if_desc_res.output["interfaceDescriptions"]
    ifs_dom = if_dom_res.output["interfaces"]

    def __ok_process_if(if_name):

        # if the interface name does not exist in the interface description data
        # it likely means that the interface name is an unused transciever lane;
        # and if so then it would be the same data as the "first lane".  In this
        # case we don't need to record a duplicate metric.

        if not (if_desc := ifs_desc.get(if_name)):
            return False

        # do not report on interfaces that are administratively disabled.

        if if_desc["interfaceStatus"] == "adminDown":
            return False

        return True

    return [
        measurement
        for if_name, if_dom_data in ifs_dom.items()
        if if_dom_data and __ok_process_if(if_name)
        for measurement in _make_if_metrics(
            if_name, if_dom_data, if_desc=ifs_desc[if_name]["description"]
        )
    ]


# -----------------------------------------------------------------------------
#
#                            PRIVATE FUNCTIONS
#
# -----------------------------------------------------------------------------


def _make_if_metrics(if_name: str, if_dom_data: dict, if_desc: str):
    """
    This function is used to create the specific IFdom Metrics for a specific
    interface.

    Parameters
    ----------
    if_name:
        The interface name

    if_dom_data:
        The interface transceiver details as retrieved via the EAPI

    if_desc:
        The interface description value

    Yields
    ------
    A collection of IFdom specific Metrics.
    """
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
        value=_threshold_outside(value=m_rxpow.value, thresholds=thresholds["rxPower"]),
        tags=c_tags,
        ts=ts,
    )

    yield ifdom.IFdomTxPowerStatusMetric(
        value=_threshold_outside(value=m_txpow.value, thresholds=thresholds["txPower"]),
        tags=c_tags,
        ts=ts,
    )

    yield ifdom.IFdomTempStatusMetric(
        value=_threshold_outside(
            value=m_temp.value, thresholds=thresholds["temperature"]
        ),
        tags=c_tags,
        ts=ts,
    )

    yield ifdom.IFdomVoltageStatusMetric(
        value=_threshold_outside(value=m_volt.value, thresholds=thresholds["voltage"]),
        tags=c_tags,
        ts=ts,
    )


def _threshold_outside(value: float, thresholds: dict) -> int:
    """
    This function determines a given metric "status" by comparing the IFdom value against
    the IFdom thresholds; which are obtained from the interface transceiver details.
    The status is encoded as (0=ok, 1=warn, 2=alert)

    Parameters
    ----------
    value:
        The interface DOM value is always a floating point number

    thresholds:
        The dictionary containing the threshold values
    """
    if value <= thresholds["lowAlarm"] or value >= thresholds["highAlarm"]:
        return 2

    if value <= thresholds["lowWarn"] or value >= thresholds["highWarn"]:
        return 1

    return 0
