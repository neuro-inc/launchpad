from pydantic import BaseModel, Field, ConfigDict


class LaunchpadAppRead(BaseModel):
    name: str = Field(alias="title", validation_alias="verbose_name")
    launchpad_app_name: str = Field(validation_alias="name")
    description_short: str = Field(serialization_alias="shortDescription")
    description_long: str = Field(serialization_alias="description")
    logo: str
    documentation_urls: list[str] = Field(serialization_alias="documentationUrls")
    external_urls: list[str] = Field(serialization_alias="externalUrls")
    tags: list[str]


class LaunchpadInstalledAppRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    launchpad_app_name: str
    is_shared: bool
    user_id: str | None
    url: str | None
