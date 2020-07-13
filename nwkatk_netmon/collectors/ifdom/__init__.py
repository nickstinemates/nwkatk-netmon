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

This file contains the Interface Digital Optical Measurement (DOM) collection
definition.

"""

from functools import singledispatch
from pydantic.dataclasses import dataclass
from pydantic import conint

from nwkatk_netmon import Metric
from nwkatk_netmon.collectors import CollectorType

# -----------------------------------------------------------------------------
#
#                              Metrics
#
# -----------------------------------------------------------------------------
# This section defines the Metric types supported by the IF DOM collector
# -----------------------------------------------------------------------------

# the status values will be encoded in the metric to mean 0=OK, 1=WARN, 2=ALERT

_IFdomStatusValue = conint(ge=0, le=2)


@dataclass
class IFdomTempMetric(Metric):
    value: float
    name: str = "ifdom_temp"


@dataclass
class IFdomTempStatusMetric(Metric):
    value: _IFdomStatusValue
    name: str = "ifdom_temp_status"


@dataclass
class IFdomRxPowerMetric(Metric):
    value: float
    name: str = "ifdom_rxpower"


@dataclass
class IFdomRxPowerStatusMetric(Metric):
    value: _IFdomStatusValue
    name: str = "ifdom_rxpower_status"


@dataclass
class IFdomTxPowerMetric(Metric):
    value: float
    name: str = "ifdom_txpower"


@dataclass
class IFdomTxPowerStatusMetric(Metric):
    value: _IFdomStatusValue
    name: str = "ifdom_txpower_status"


@dataclass
class IFdomVoltageMetric(Metric):
    value: float
    name: str = "ifdom_voltage"


@dataclass
class IFdomVoltageStatusMetric(Metric):
    value: _IFdomStatusValue
    name: str = "ifdom_voltag_status"


# -----------------------------------------------------------------------------
#
#                              Collector Definition
#
# -----------------------------------------------------------------------------


@singledispatch
async def ifdom_start(device, executor, **kwargs):  # noqa
    """
    Using a "singledispatch" method for driver-specific registration purposes. A
    specific device driver collector package will use this function as a
    decorator to register their specific Driver class.  See the eapi.py and
    nxapi.py files to see how this is used.

    In the event that the system attempts to start collecting on an unsupported
    (unregistered) Device class the body of this function will be called; which
    will raise a RuntimeError.
    """
    cls_name = device.__class__.__name__
    raise RuntimeError(f"IFdom: No entry-point registered for device type: {cls_name}")


class IFdomCollectorSpec(CollectorType):
    """
    This class defines the Interface DOM Collector specification.  This class is
    "registered" with the "nwka_netmon.collectors" entry_point group via the
    `setup.py` file.  As a result of this registration, a User of the
    nwka-netmon tool can setup their configuration file with the "use"
    statement.

    Examples (Configuration File)
    -----------------------------
    [collectors.ifdom]
        use = "nwka_netmon.collectors:ifdom"

    """

    start = ifdom_start
    metrics = [
        IFdomRxPowerMetric,
        IFdomRxPowerStatusMetric,
        IFdomTxPowerMetric,
        IFdomTxPowerStatusMetric,
        IFdomTempMetric,
        IFdomTempStatusMetric,
        IFdomVoltageMetric,
        IFdomVoltageStatusMetric,
    ]


# create an "alias" variable so that the device specific collector packages
# can register their start functions.

register = IFdomCollectorSpec.start.register
