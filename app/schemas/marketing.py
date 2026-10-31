"""Marketing library and analytics schemas."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductFAQ(BaseModel):
    question: str
    answer: str


class ProductProfileData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=200)
    category: str = ""
    description: str = ""
    core_features: list[str] = Field(default_factory=list, alias="coreFeatures")
    target_audience: str = Field(default="", alias="targetAudience")
    selling_points: list[str] = Field(default_factory=list, alias="sellingPoints")
    differentiators: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list, alias="useCases")
    brand_tone: str = Field(default="", alias="brandTone")
    claims_to_avoid: list[str] = Field(default_factory=list, alias="claimsToAvoid")
    faq: list[ProductFAQ] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class ProductProfileVO(BaseModel):
    id: int
    name: str
    source_filename: str = Field(alias="sourceFilename")
    profile: ProductProfileData
    create_time: str = Field(alias="createTime")

    model_config = ConfigDict(populate_by_name=True)


class MarketingPlatformVO(BaseModel):
    id: int
    platform_key: str = Field(alias="platformKey")
    name: str
    audience_description: str = Field(alias="audienceDescription")
    content_rules: str = Field(alias="contentRules")
    preferred_formats: str = Field(alias="preferredFormats")

    model_config = ConfigDict(populate_by_name=True)


class MarketingPlatformUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    audience_description: str = Field(alias="audienceDescription", min_length=1)
    content_rules: str = Field(alias="contentRules", min_length=1)
    preferred_formats: str = Field(alias="preferredFormats", min_length=1)

    model_config = ConfigDict(populate_by_name=True)


class MarketingAnalysisRequest(BaseModel):
    question: Optional[str] = None
