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

