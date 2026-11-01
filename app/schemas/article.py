"""文章相关请求/响应模型"""

from typing import Optional, List, Any
from pydantic import BaseModel, Field
from app.agent.provenance import MaterialInput

from app.schemas.common import PageRequest


class ArticleCreateRequest(BaseModel):
    """创建文章请求（新增风格和配图方式选择）"""

    topic: str = Field(..., min_length=1, description="选题")
    style: Optional[str] = Field(None, description="文章风格：tech/emotional/educational/humorous")
    product_id: Optional[int] = Field(None, alias="productId", description="产品档案 ID")
    platform_id: int = Field(..., alias="platformId", ge=1, description="营销平台 ID")
    enabled_image_methods: Optional[List[str]] = Field(
        None,
        alias="enabledImageMethods",
        description="允许的配图方式列表（为空表示支持所有方式）"
    )


class ArticleQueryRequest(PageRequest):
    """文章查询请求"""

    id: Optional[int] = Field(None, description="文章 ID")
    task_id: Optional[str] = Field(None, alias="taskId", description="任务 ID")
    user_id: Optional[int] = Field(None, alias="userId", description="用户 ID")
    topic: Optional[str] = Field(None, description="选题")
    status: Optional[str] = Field(None, description="状态")


class TitleOption(BaseModel):
    """标题方案"""

    main_title: str = Field(..., alias="mainTitle")
    sub_title: str = Field(..., alias="subTitle")

    class Config:
        populate_by_name = True


class ArticleVO(BaseModel):
    """文章视图对象"""

    id: int
    task_id: str = Field(..., alias="taskId")
    user_id: int = Field(..., alias="userId")
    product_id: Optional[int] = Field(None, alias="productId")
    platform_id: Optional[int] = Field(None, alias="platformId")
    topic: str
    user_description: Optional[str] = Field(None, alias="userDescription")
    style: Optional[str] = None
    main_title: Optional[str] = Field(None, alias="mainTitle")
    sub_title: Optional[str] = Field(None, alias="subTitle")
    title_options: Optional[List[TitleOption]] = Field(None, alias="titleOptions")
    outline: Optional[List[Any]] = None
    content: Optional[str] = None
    full_content: Optional[str] = Field(None, alias="fullContent")
    cover_image: Optional[str] = Field(None, alias="coverImage")
    images: Optional[List[Any]] = None
    status: str
    phase: Optional[str] = None
    error_message: Optional[str] = Field(None, alias="errorMessage")
    create_time: str = Field(..., alias="createTime")
    completed_time: Optional[str] = Field(None, alias="completedTime")
    update_time: str = Field(..., alias="updateTime")

    class Config:
        populate_by_name = True


# ArticleState 内部类定义
class TitleResult(BaseModel):
    """标题结果"""

    main_title: str = Field(..., alias="mainTitle")
    sub_title: str = Field(..., alias="subTitle")

    class Config:
        populate_by_name = True


class OutlineSection(BaseModel):
    """大纲章节"""

    section: int
    title: str
    points: List[str]


class OutlineResult(BaseModel):
    """大纲结果"""

    sections: List[OutlineSection]


class ImageRequirement(BaseModel):
    """配图需求；表情包来源只需要保存工具返回的 memeId。"""

    position: int
    type: str
    section_title: str = Field(..., alias="sectionTitle")
    keywords: Optional[str] = None
    image_source: str = Field(..., alias="imageSource", description="图片来源")
    prompt: str = Field(default="", description="AI 生图提示词")
    meme_id: Optional[str] = Field(None, alias="memeId", description="表情包候选 ID")
    placeholder_id: str = Field(..., alias="placeholderId", description="占位符ID")

    class Config:
        populate_by_name = True


class ImageResult(BaseModel):
    """配图结果（新增 placeholderId）"""

    position: int
    url: str
    method: str
    keywords: str
    section_title: str = Field(..., alias="sectionTitle")
    description: str
    placeholder_id: str = Field(..., alias="placeholderId", description="占位符ID")

    class Config:
        populate_by_name = True


class Agent4Result(BaseModel):
    """智能体4返回结果（占位符方案）"""

    content_with_placeholders: str = Field(..., alias="contentWithPlaceholders")
    image_requirements: List[ImageRequirement] = Field(..., alias="imageRequirements")

    class Config:
        populate_by_name = True


class ArticleState:
    """文章生成状态（智能体间共享的状态对象）"""

    def __init__(self):
        self.task_id: Optional[str] = None
        self.topic: Optional[str] = None
        self.user_description: Optional[str] = None
        self.style: Optional[str] = None
        self.phase: Optional[str] = None
        self.title_options: Optional[List[TitleOption]] = None
        self.enabled_image_methods: Optional[List[str]] = None
        self.title: Optional[TitleResult] = None
        self.outline: Optional[OutlineResult] = None
        self.content: Optional[str] = None
        self.image_requirements: Optional[List[ImageRequirement]] = None
        self.meme_candidates: dict[str, dict[str, str]] = {}
        self.images: Optional[List[ImageResult]] = None
        self.cover_image: Optional[str] = None
        self.full_content: Optional[str] = None
        self.owner_id: Optional[int] = None
        self.product_id: Optional[int] = None
        self.platform_id: Optional[int] = None
        self.marketing_context: Optional[str] = None
        self.marketing_sources: list[MaterialInput] = []


class ArticleConfirmTitleRequest(BaseModel):
    """确认标题请求"""

    task_id: str = Field(..., alias="taskId", min_length=1)
    selected_main_title: str = Field(..., alias="selectedMainTitle", min_length=1)
    selected_sub_title: str = Field(..., alias="selectedSubTitle", min_length=1)
    user_description: Optional[str] = Field(None, alias="userDescription")

    class Config:
        populate_by_name = True


class ArticleConfirmOutlineRequest(BaseModel):
    """确认大纲请求"""

    task_id: str = Field(..., alias="taskId", min_length=1)
    outline: List[OutlineSection] = Field(..., min_length=1)

    class Config:
        populate_by_name = True


class ArticleAiModifyOutlineRequest(BaseModel):
    """AI 修改大纲请求"""

    task_id: str = Field(..., alias="taskId", min_length=1)
    modify_suggestion: str = Field(..., alias="modifySuggestion", min_length=1)

    class Config:
        populate_by_name = True
