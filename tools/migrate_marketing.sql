-- Run once on an existing database to add the marketing library schema.
USE ai_passage_creator;

ALTER TABLE article
    ADD COLUMN productId BIGINT NULL COMMENT '产品档案ID',
    ADD COLUMN platformId BIGINT NULL COMMENT '营销平台ID';

CREATE TABLE IF NOT EXISTS product_profile
(
    id             BIGINT AUTO_INCREMENT COMMENT 'id' PRIMARY KEY,
    ownerId        BIGINT                             NOT NULL COMMENT '所属用户ID',
    name           VARCHAR(200)                       NOT NULL COMMENT '产品名称',
    sourceFilename VARCHAR(255)                       NOT NULL COMMENT '来源文件名',
    profile        JSON                               NOT NULL COMMENT 'AI 整理后的标准产品档案',
    createTime     DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updateTime     DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL ON UPDATE CURRENT_TIMESTAMP,
    isDelete       TINYINT  DEFAULT 0                 NOT NULL,
    INDEX idx_product_owner (ownerId, isDelete),
    INDEX idx_product_name (name)
) COMMENT '产品档案' COLLATE = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS marketing_platform
(
    id                  BIGINT AUTO_INCREMENT COMMENT 'id' PRIMARY KEY,
    platformKey         VARCHAR(64)                        NOT NULL COMMENT '平台唯一标识',
    name                VARCHAR(100)                       NOT NULL COMMENT '平台名称',
    audienceDescription TEXT                               NOT NULL COMMENT '受众特点',
    contentRules        TEXT                               NOT NULL COMMENT '内容规则',
    preferredFormats    TEXT                               NOT NULL COMMENT '推荐内容形式',
    updateTime          DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL ON UPDATE CURRENT_TIMESTAMP,
    isDelete            TINYINT  DEFAULT 0                 NOT NULL,
    UNIQUE KEY uk_platform_key (platformKey)
) COMMENT '营销平台资料' COLLATE = utf8mb4_unicode_ci;

INSERT INTO marketing_platform (platformKey, name, audienceDescription, contentRules, preferredFormats)
SELECT 'xiaohongshu', '小红书', '以年轻女性为主，关注生活方式、消费决策、真实体验和可收藏的实用信息。',
       '标题和封面要清晰具体；使用自然口语和真实体验表达；避免夸大功效、虚假种草及站外导流；适合分点表达和明确话题标签。',
       '经验分享、清单攻略、前后对比（有真实依据时）、图文笔记、短视频'
WHERE NOT EXISTS (SELECT 1 FROM marketing_platform WHERE platformKey = 'xiaohongshu');

INSERT INTO marketing_platform (platformKey, name, audienceDescription, contentRules, preferredFormats)
SELECT 'wechat', '微信公众号', '适合关注品牌、行业和深度信息的订阅用户，阅读场景以完整文章和持续服务为主。',
       '标题准确且有信息量；开篇尽快说明价值；正文结构清晰、论据可信；避免标题与内容不符及未经证实的结论。',
       '深度文章、产品指南、案例拆解、服务通知、系列内容'
WHERE NOT EXISTS (SELECT 1 FROM marketing_platform WHERE platformKey = 'wechat');

INSERT INTO marketing_platform (platformKey, name, audienceDescription, contentRules, preferredFormats)
SELECT 'douyin', '抖音', '偏好短时长、强节奏和直观演示的移动端用户，内容发现以推荐流和视频互动为主。',
       '前几秒呈现主题或结果；口播自然、镜头信息明确；画面和文案简洁；避免虚假承诺、误导性对比和违规营销。',
       '短视频脚本、口播、情景演示、直播提纲、字幕文案'
WHERE NOT EXISTS (SELECT 1 FROM marketing_platform WHERE platformKey = 'douyin');
