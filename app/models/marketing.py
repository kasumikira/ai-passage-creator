"""Marketing library ORM models."""

from sqlalchemy import BigInteger, Column, DateTime, SmallInteger, String, Text
from sqlalchemy.sql import func

from app.database import Base


class ProductProfile(Base):
    __tablename__ = "product_profile"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    owner_id = Column("ownerId", BigInteger, nullable=False)
    name = Column(String(200), nullable=False)
    source_filename = Column("sourceFilename", String(255), nullable=False)
    profile = Column(Text, nullable=False, comment="AI 标准化产品档案 JSON")
    create_time = Column("createTime", DateTime, nullable=False, default=func.now())
    update_time = Column("updateTime", DateTime, nullable=False, default=func.now(), onupdate=func.now())
    is_delete = Column("isDelete", SmallInteger, nullable=False, default=0)


class MarketingPlatform(Base):
    __tablename__ = "marketing_platform"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    platform_key = Column("platformKey", String(64), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    audience_description = Column("audienceDescription", Text, nullable=False)
    content_rules = Column("contentRules", Text, nullable=False)
    preferred_formats = Column("preferredFormats", Text, nullable=False)
    update_time = Column("updateTime", DateTime, nullable=False, default=func.now(), onupdate=func.now())
    is_delete = Column("isDelete", SmallInteger, nullable=False, default=0)
