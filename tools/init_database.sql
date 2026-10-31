-- 完整数据库初始化脚本：建库、建表及初始数据
-- 适用于全新数据库初始化

# 数据库初始化（基础表结构）
# @author <a href="https://codefather.cn">编程导航学习圈</a>
# 完整数据库初始化脚本（包含原增量脚本中的字段）

-- 设置字符集（解决中文乱码问题）
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- 创建库
CREATE DATABASE IF NOT EXISTS ai_passage_creator CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 切换库
USE ai_passage_creator;

-- 用户表
CREATE TABLE IF NOT EXISTS user
(
    id           BIGINT AUTO_INCREMENT COMMENT 'id' PRIMARY KEY,
    userAccount  VARCHAR(256)                           NOT NULL COMMENT '账号',
    userPassword VARCHAR(512)                           NOT NULL COMMENT '密码',
    userName     VARCHAR(256)                           NULL COMMENT '用户昵称',
    userAvatar   VARCHAR(1024)                          NULL COMMENT '用户头像',
    userProfile  VARCHAR(512)                           NULL COMMENT '用户简介',
    userRole     VARCHAR(256) DEFAULT 'user'            NOT NULL COMMENT '用户角色：user/admin',
    editTime     DATETIME     DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '编辑时间',
    createTime   DATETIME     DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '创建时间',
    updateTime   DATETIME     DEFAULT CURRENT_TIMESTAMP NOT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    isDelete     TINYINT      DEFAULT 0                 NOT NULL COMMENT '是否删除',
    UNIQUE KEY uk_userAccount (userAccount),
    INDEX idx_userName (userName)
) COMMENT '用户' COLLATE = utf8mb4_unicode_ci;

-- 初始化数据
-- 密码是 12345678（MD5 加密 + 盐值 yupi）
-- 根据 userAccount 判断是否已存在；不指定 id，避免与现有用户主键冲突
INSERT INTO user (userAccount, userPassword, userName, userAvatar, userProfile, userRole)
SELECT 'admin', '10670d38ec32fa8102be6a37f8cb52bf', '管理员', 'https://www.codefather.cn/logo.png', '系统管理员', 'admin'
WHERE NOT EXISTS (SELECT 1 FROM user WHERE userAccount = 'admin');

INSERT INTO user (userAccount, userPassword, userName, userAvatar, userProfile, userRole)
SELECT 'user', '10670d38ec32fa8102be6a37f8cb52bf', '普通用户', 'https://www.codefather.cn/logo.png', '我是一个普通用户', 'user'
WHERE NOT EXISTS (SELECT 1 FROM user WHERE userAccount = 'user');

INSERT INTO user (userAccount, userPassword, userName, userAvatar, userProfile, userRole)
SELECT 'test', '10670d38ec32fa8102be6a37f8cb52bf', '测试账号', 'https://www.codefather.cn/logo.png', '这是一个测试账号', 'user'
WHERE NOT EXISTS (SELECT 1 FROM user WHERE userAccount = 'test');

-- 文章表
CREATE TABLE IF NOT EXISTS article
(
    id              BIGINT AUTO_INCREMENT COMMENT 'id' PRIMARY KEY,
    taskId          VARCHAR(64)                        NOT NULL COMMENT '任务ID（UUID）',
    userId          BIGINT                             NOT NULL COMMENT '用户ID',
    productId       BIGINT                             NULL COMMENT '产品档案ID',
    platformId      BIGINT                             NULL COMMENT '营销平台ID',
    topic           VARCHAR(500)                       NOT NULL COMMENT '选题',
    style           VARCHAR(20) NULL COMMENT '文章风格：tech/emotional/educational/humorous',
    userDescription TEXT NULL COMMENT '用户补充描述',
    enabledImageMethods JSON NULL COMMENT '允许的配图方式列表',
    mainTitle       VARCHAR(200)                       NULL COMMENT '主标题',
    subTitle        VARCHAR(300)                       NULL COMMENT '副标题',
    titleOptions    JSON NULL COMMENT '标题方案列表（3-5个方案）',
    outline         JSON                               NULL COMMENT '大纲（JSON格式）',
    content         TEXT                               NULL COMMENT '正文（Markdown格式）',
    fullContent     TEXT                               NULL COMMENT '完整图文（Markdown格式，含配图）',
    coverImage      VARCHAR(512)                       NULL COMMENT '封面图 URL',
    images          JSON                               NULL COMMENT '配图列表（JSON数组，包含封面图 position=1）',
    status          VARCHAR(20) DEFAULT 'PENDING'      NOT NULL COMMENT '状态：PENDING/PROCESSING/COMPLETED/FAILED',
    phase           VARCHAR(50) DEFAULT 'PENDING' COMMENT '当前阶段：PENDING/TITLE_GENERATING/TITLE_SELECTING/OUTLINE_GENERATING/OUTLINE_EDITING/CONTENT_GENERATING',
    errorMessage    TEXT                               NULL COMMENT '错误信息',
    createTime      DATETIME    DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '创建时间',
    completedTime   DATETIME                           NULL COMMENT '完成时间',
    updateTime      DATETIME    DEFAULT CURRENT_TIMESTAMP NOT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    isDelete        TINYINT     DEFAULT 0              NOT NULL COMMENT '是否删除',
    UNIQUE KEY uk_taskId (taskId),
    INDEX idx_userId (userId),
    INDEX idx_status (status),
    INDEX idx_createTime (createTime),
    INDEX idx_userId_status (userId, status)
) COMMENT '文章表' COLLATE = utf8mb4_unicode_ci;

-- 产品档案（原始文档只在解析时使用，标准档案以 JSON 保存）
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

-- 营销平台规则和受众资料
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

-- 智能体执行日志表
CREATE TABLE IF NOT EXISTS agent_log
(
    id              BIGINT AUTO_INCREMENT COMMENT 'id' PRIMARY KEY,
    taskId          VARCHAR(64)                        NOT NULL COMMENT '任务ID',
    agentName       VARCHAR(50)                        NOT NULL COMMENT '智能体名称',
    startTime       DATETIME                           NOT NULL COMMENT '开始时间',
    endTime         DATETIME                           NULL COMMENT '结束时间',
    durationMs      INT                                NULL COMMENT '耗时（毫秒）',
    status          VARCHAR(20)                        NOT NULL COMMENT '状态：SUCCESS/FAILED',
    errorMessage    TEXT                               NULL COMMENT '错误信息',
    prompt          TEXT                               NULL COMMENT '使用的Prompt',
    inputData       JSON                               NULL COMMENT '输入数据（JSON格式）',
    outputData      JSON                               NULL COMMENT '输出数据（JSON格式）',
    createTime      DATETIME    DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '创建时间',
    updateTime      DATETIME    DEFAULT CURRENT_TIMESTAMP NOT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    isDelete        TINYINT     DEFAULT 0              NOT NULL COMMENT '是否删除',
    INDEX idx_taskId (taskId),
    INDEX idx_agentName (agentName),
    INDEX idx_status (status),
    INDEX idx_createTime (createTime)
) COMMENT '智能体执行日志表' COLLATE = utf8mb4_unicode_ci;

