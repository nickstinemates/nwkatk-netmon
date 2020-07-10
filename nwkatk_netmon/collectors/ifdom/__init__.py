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

from functools import singledispatch
from pydantic.dataclasses import dataclass
from pydantic import conint

from nwkatk_netmon import Metric


@singledispatch
async def ifdom_start(device, **kwargs):  # noqa
    cls_name = device.__class__.__name__
    raise RuntimeError(f"IFdom: No entry-point registered for device type: {cls_name}")


IFdomStatusValue = conint(ge=0, le=2)


@dataclass
class IFdomTempMetric(Metric):
    value: float
    name: str = "ifdom_temp"


@dataclass
class IFdomTempStatusMetric(Metric):
    value: IFdomStatusValue
    name: str = "ifdom_temp_status"


@dataclass
class IFdomRxPowerMetric(Metric):
    value: float
    name: str = "ifdom_rxpower"


@dataclass
class IFdomRxPowerStatusMetric(Metric):
    value: IFdomStatusValue
    name: str = "ifdom_rxpower_status"


@dataclass
class IFdomTxPowerMetric(Metric):
    value: float
    name: str = 'ifdom_txpower'


@dataclass
class IFdomTxPowerStatusMetric(Metric):
    value: IFdomStatusValue
    name: str = "ifdom_txpower_status"


@dataclass
class IFdomVoltageMetric(Metric):
    value: float
    name: str = "ifdom_voltage"


@dataclass
class IFdomVoltageStatusMetric(Metric):
    value: IFdomStatusValue
    name: str = "ifdom_voltag_status"
