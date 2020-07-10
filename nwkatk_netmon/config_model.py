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

from typing import Dict, Callable, Optional, List

from . import consts

from pydantic import (
    BaseSettings,
    Field,
    ValidationError,  # noqa
    PositiveInt,
    validator,
)


from nwkatk.config_model import (
    NoExtraBaseModel,
    EnvExpand,
    EnvSecretStr,
    Credential,
    EntryPointImportPath, ImportPath,
    FilePathEnvExpand,
)


class DefaultCredential(Credential, BaseSettings):
    username: EnvExpand
    password: EnvSecretStr


class DefaultsModel(NoExtraBaseModel, BaseSettings):
    interval: Optional[PositiveInt] = Field(default=consts.DEFAULT_INTERVAL)
    inventory: FilePathEnvExpand
    credentials: DefaultCredential


class OSNameModel(NoExtraBaseModel):
    driver: Callable
    packages: List[ImportPath]

    @validator('driver', pre=True)
    def _to_callable(cls, val):
        return EntryPointImportPath.validate(val)


class ConfigModel(NoExtraBaseModel):
    defaults: DefaultsModel
    os_name: Dict[str, OSNameModel]
    collectors: Dict[str, Callable]
    collector_configs: Optional[Dict[str, Dict]] = Field(default_factory=lambda: {})

    @validator('collectors', pre=True, each_item=True)
    def _to_callable(cls, val):
        return EntryPointImportPath.validate(val)
