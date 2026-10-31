"""配置管理"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """应用配置（AI 核心创作流程）"""

    # 服务器配置
    server_port: int = 8567
    server_host: str = "0.0.0.0"

    # 数据库配置
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "ai_passage_creator"
    db_user: str = "root"
    db_password: str = "1234"

    # Redis 配置
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = "1234"

    # Session 配置
    session_secret_key: str = "93ac288c31eef99e2c2de8c60236129f4ed121cfca1e10241a67e4140c360913"
    session_max_age: int = 2592000  # 30 天

    # 密码加密盐值
    password_salt: str = "yupi"

    # AI 文本生成配置（OpenAI 兼容协议，默认 DeepSeek 官方端点）
    llm_api_key: str = "dummy"
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-flash"
    llm_reasoning_effort: Optional[str] = None

    # Pexels 图片搜索
    pexels_api_key: str = "dummy"
    pexels_api_url: str = "https://api.pexels.com/v1/search"

    # AI 生图配置（格式：google-genai=Google GenAI 协议 / openai=OpenAI images 兼容协议）
    image_gen_format: str = "google-genai"
    image_gen_api_key: str = "dummy"
    image_gen_base_url: str = ""  # 留空使用所选格式的官方端点
    image_gen_model: str = "gemini-2.5-flash-image"
    image_gen_aspect_ratio: str = "16:9"
    image_gen_image_size: str = "1K"
    image_gen_output_mime_type: str = "image/png"

    # Mermaid 配置
    mermaid_background_color: str = "transparent"
    mermaid_output_format: str = "svg"
    mermaid_width: int = 1200

    # Iconify 配置
    iconify_api_url: str = "https://api.iconify.design"
    iconify_search_limit: int = 10
    iconify_default_height: int = 64
    iconify_default_color: str = ""

    # 表情包配置
    meme_search_url: str = "https://cn.bing.com/images/async"
    meme_suffix: str = "表情包"
    meme_timeout: int = 10000
    meme_default_limit: int = 3

    # SVG 示意图配置
    svg_diagram_default_width: int = 800
    svg_diagram_default_height: int = 600
    svg_diagram_folder: str = "svg-diagrams"

    # 多智能体并行编排配置
    agent_image_max_concurrency: int = 3

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def database_url(self) -> str:
        """获取数据库连接 URL"""
        return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"

    @property
    def redis_url(self) -> str:
        """获取 Redis 连接 URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


settings = Settings()
