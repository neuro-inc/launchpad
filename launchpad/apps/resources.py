from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ImportTemplateRequest(BaseModel):
    """Request model for importing a template from Apps API"""

    template_name: str = Field(..., description="The template name from Apps API")
    template_version: str = Field(..., description="The template version from Apps API")
    name: str | None = Field(
        None, description="Custom name for the template (defaults to template_name)"
    )
    verbose_name: str | None = Field(None, description="User-friendly display name")
    description_short: str | None = Field(None, description="Short description")
    description_long: str | None = Field(None, description="Long description")
    logo: str | None = Field(None, description="URL to the template's logo")
    documentation_urls: list[dict[str, str]] | None = Field(
        None, description="Documentation URLs"
    )
    external_urls: list[dict[str, str]] | None = Field(
        None, description="External URLs"
    )
    tags: list[str] | None = Field(None, description="Tags for categorization")
    is_internal: bool = Field(default=False, description="Whether template is internal")
    is_shared: bool = Field(
        default=True, description="Whether apps from this template can be shared"
    )
    default_inputs: dict[str, Any] = Field(
        default_factory=dict,
        description="Default inputs to merge with user-provided inputs when installing",
    )


class ImportAppRequest(BaseModel):
    """Request model for importing an externally installed app"""

    app_id: UUID = Field(..., description="The app_id from Apps API to import")
    name: str | None = Field(
        None, description="Custom name for the app (defaults to template_name)"
    )
    verbose_name: str | None = Field(None, description="User-friendly display name")
    description_short: str | None = Field(None, description="Short description")
    description_long: str | None = Field(None, description="Long description")
    logo: str | None = Field(None, description="URL to the app's logo")
    documentation_urls: list[dict[str, str]] | None = Field(
        None, description="Documentation URLs"
    )
    external_urls: list[dict[str, str]] | None = Field(
        None, description="External URLs"
    )
    tags: list[str] | None = Field(None, description="Tags for categorization")
    is_internal: bool = Field(default=False, description="Whether app is internal")


class GenericAppInstallRequest(BaseModel):
    """Request model for installing a generic app with custom configuration"""

    template_name: str = Field(..., description="Name of the template to install")
    template_version: str = Field(..., description="Version of the template")
    inputs: dict[str, Any] = Field(..., description="Inputs to pass to the Apps API")
    name: str | None = Field(
        None, description="Custom name for the app (defaults to template_name)"
    )
    verbose_name: str | None = Field(None, description="User-friendly display name")
    description_short: str = Field(default="", description="Short description")
    description_long: str = Field(default="", description="Long description")
    logo: str = Field(default="", description="URL to the app's logo")
    documentation_urls: list[dict[str, str]] = Field(
        default_factory=list, description="Documentation URLs"
    )
    external_urls: list[dict[str, str]] = Field(
        default_factory=list, description="External URLs"
    )
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    is_internal: bool = Field(default=False, description="Whether app is internal")
    is_shared: bool = Field(default=True, description="Whether app can be shared")


class LaunchpadAppRead(BaseModel):
    name: str = Field(alias="title", validation_alias="verbose_name")
    launchpad_app_name: str = Field(validation_alias="name")
    description_short: str
    description_long: str
    logo: str
    documentation_urls: list[dict[str, str]]
    external_urls: list[dict[str, str]]
    tags: list[str]


class LaunchpadTemplateRead(BaseModel):
    """Response model for template data"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    template_name: str
    template_version: str
    verbose_name: str
    description_short: str
    description_long: str
    logo: str
    documentation_urls: list[dict[str, str]]
    external_urls: list[dict[str, str]]
    tags: list[str]
    is_internal: bool
    is_shared: bool
    default_inputs: dict[str, Any]


class LaunchpadInstalledAppRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    launchpad_app_name: str
    is_shared: bool
    user_id: str | None
    url: str | None
