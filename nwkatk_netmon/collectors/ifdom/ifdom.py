from functools import singledispatch
from pydantic import BaseModel


class IfdomMetricTags(BaseModel):
    if_name: str
    if_desc: str
    media: str


class IfdomMetrics(BaseModel):
    txpower: float
    txpower_status: int
    rxpower: float
    rxpower_status: int
    temp: float
    temp_status: int
    voltage: float
    voltage_status: int


@singledispatch
async def ifdom_start(device, **kwargs):  # noqa
    pass
