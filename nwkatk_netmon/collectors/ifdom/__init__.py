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
from typing import Optional
from pydantic.dataclasses import dataclass
from pydantic import conint, Field

from nwkatk_netmon import Metric
from nwkatk_netmon.collectors import CollectorType, CollectorConfigModel

# -----------------------------------------------------------------------------
#
#                              Collector Config
# -----------------------------------------------------------------------------
# Define the collector configuraiton options that the User can set in their
# configuration file.
# -----------------------------------------------------------------------------


class IFdomCollectorConfig(CollectorConfigModel):
    include_linkdown: Optional[bool] = Field(
        default=False,
        description="""
Controls whether or not to report on interfaces when the link is down.  When
False (default), only interfaces that are link-up are included.  When True, all
interfaces with optics installed will be included, even if they are link-down.
""",
    )


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


class IFdomCollector(CollectorType):
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

    config = IFdomCollectorConfig

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

register = IFdomCollector.start.register
