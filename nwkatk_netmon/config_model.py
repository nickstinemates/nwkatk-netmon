from typing import Dict, Union, Callable, Optional

from . import consts

from pydantic import (
    BaseSettings, Field,
    ValidationError,  # noqa
    PositiveInt, validator
)


from nwkatk.config_model import (
    NoExtraBaseModel,
    EnvExpand, EnvSecretStr,
    Credential, EntryPointImportPath,
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
    driver: Union[EntryPointImportPath, Callable]


class ConfigModel(NoExtraBaseModel):
    defaults: DefaultsModel
    os_name: Dict[str, OSNameModel]
    collectors: Dict[str, Union[EntryPointImportPath, Callable]]
    collector_configs: Optional[Dict[str, Dict]]

    @validator('collector_configs', always=True)
    def _ensure_collector_configs(cls, value):      # noqa
        return value or {}
