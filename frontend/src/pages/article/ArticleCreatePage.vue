<template>
  <div class="article-create-page">
    <!-- 三栏布局容器 -->
    <div class="create-layout">
      <!-- 左侧：智能体流程可视化 -->
      <aside class="sidebar-left">
        <div class="sidebar-header">
          <h3 class="sidebar-title">创作流程</h3>
          <p class="sidebar-subtitle">智能体协作可视化</p>
        </div>

        <div class="flow-timeline">
          <div
            v-for="(step, index) in agentSteps"
            :key="index"
            :class="['flow-item', {
              'active': currentStep === index,
              'completed': currentStep > index,
              'pending': currentStep < index
            }]"
          >
            <div class="flow-indicator">
              <LoadingOutlined v-if="currentStep === index && isCreating" class="spin-icon" />
              <CheckCircleOutlined v-else-if="currentStep > index" />
              <span v-else class="step-number">{{ index + 1 }}</span>
            </div>
            <div class="flow-content">
              <div class="flow-title">{{ step.title }}</div>
              <div class="flow-desc">{{ step.description }}</div>
              <div v-if="currentStep === index && isCreating" class="flow-status">
                <span class="status-dot"></span>
                执行中...
              </div>
            </div>
          </div>
        </div>

      </aside>

      <!-- 中间：主内容区 -->
      <main class="main-content">
        <!-- AI 推理与工具调用在主内容区按事件顺序连续展示 -->
        <section v-if="realtimeLogs.length > 0" class="central-process-panel">
          <div class="process-heading">
            <div class="process-heading-main">
              <span class="process-live-dot" aria-hidden="true"></span>
              <h4 class="panel-title">
                <ThunderboltOutlined />
                AI 推理与工具调用
              </h4>
              <span class="process-live-label">实时</span>
            </div>
            <button type="button" class="process-toggle" @click="processExpanded = !processExpanded">
              {{ processExpanded ? '收起过程' : '查看过程' }}
            </button>
          </div>
          <div v-if="activeToolCall" class="tool-call-banner">
            <LoadingOutlined class="process-spinner" />
            <div class="tool-call-copy">
              <strong>AI 正在进行工具调用</strong>
              <span>
                {{ activeToolCall.label }}
                <template v-if="activeToolCall.query"> · {{ activeToolCall.query }}</template>
              </span>
            </div>
            <span class="tool-call-state">RUNNING</span>
          </div>
          <div
            v-if="activeAgentProgress"
            :class="['process-summary', activeAgentProgress.status]"
          >
            <LoadingOutlined v-if="activeAgentProgress.status === 'started'" class="process-spinner" />
            <CheckCircleOutlined v-else-if="activeAgentProgress.status === 'completed'" />
            <CloseCircleOutlined v-else />
            <span><strong>{{ activeAgentProgress.title }}</strong> · {{ activeAgentProgress.summary }}</span>
          </div>
          <Transition name="expand">
            <div v-show="processExpanded" ref="logsContainerRef" class="logs-container">
              <div
                v-for="log in realtimeLogs"
                :key="log.id"
                :class="['log-entry', log.level, log.kind]"
              >
                <template v-if="log.kind === 'reasoning'">
                  <div class="reasoning-label">
                    <span class="reasoning-mark" aria-hidden="true"></span>
                    reasoning
                  </div>
                  <div class="log-message reasoning-message">{{ log.message }}</div>
                </template>
                <template v-else-if="log.kind === 'tool'">
                  <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
                  <span class="log-tool-icon">
                    <LoadingOutlined v-if="log.status === 'running'" class="process-spinner" />
                    <CheckCircleOutlined v-else-if="log.status === 'completed'" />
                    <CloseCircleOutlined v-else />
                  </span>
                  <div class="log-tool-copy">
                    <strong>
                      {{ log.status === 'running' ? 'AI 正在调用工具' : log.status === 'completed' ? '工具调用完成' : '工具调用失败' }}
                    </strong>
                    <span class="log-message">{{ log.message }}</span>
                  </div>
                </template>
                <template v-else-if="log.kind === 'meme-result'">
                  <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
                  <div class="meme-result-copy">
                    <strong>返回表情包候选图</strong>
                    <span class="log-message">{{ log.message }}</span>
                    <div class="meme-candidate-grid">
                      <div
                        v-for="item in log.memeItems"
                        :key="item.memeId"
                        class="meme-candidate"
                      >
                        <span class="meme-candidate-id">{{ item.memeId }}</span>
                        <img :src="item.imageUrl" :alt="item.memeId" loading="lazy" />
                      </div>
                    </div>
                  </div>
                </template>
                <template v-else>
                  <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
                  <span class="log-message">{{ log.message }}</span>
                </template>
              </div>
            </div>
          </Transition>
        </section>

        <!-- 阶段切换（带过渡动画） -->
        <Transition name="fade-slide" mode="out-in">
          <!-- 输入状态 -->
          <div v-if="currentPhase === 'INPUT'" key="input" class="input-state">
          <div class="input-card">
            <div class="input-header">
              <h1 class="input-title">新建营销内容</h1>
              <p class="input-subtitle">选择发布平台并关联产品，AI 按受众和规则完成创作</p>
            </div>

            <div class="input-area">
              <a-textarea
                v-model:value="topic"
                placeholder="描述本次营销主题或内容需求，例如：为换季护肤产品创作一条短视频脚本"
                :rows="6"
                :maxlength="500"
                show-count
                class="topic-textarea"
              />

              <div class="context-select-grid">
                <label class="context-field">
                  <span>发布平台 <i>必选</i></span>
                  <a-select v-model:value="selectedPlatformId" placeholder="选择内容发布平台">
                    <a-select-option v-for="platform in platforms" :key="platform.id" :value="platform.id">
                      {{ platform.name }}
                    </a-select-option>
                  </a-select>
                </label>
                <label class="context-field">
                  <span>关联产品 <i>可选</i></span>
                  <a-select
                    v-model:value="selectedProductId"
                    allow-clear
                    placeholder="选择产品档案"
                    :disabled="products.length === 0"
                  >
                    <a-select-option v-for="product in products" :key="product.id" :value="product.id">
                      {{ product.name }}
                    </a-select-option>
                  </a-select>
                </label>
              </div>
              <div v-if="selectedPlatform" class="context-hint">
                AI 将遵循 {{ selectedPlatform.name }} 的受众特点、内容规则与推荐形式。
                <span v-if="products.length === 0">可先到「资料库」上传产品文档。</span>
              </div>

              <!-- 文章风格选择 -->
              <div class="style-section">
                <div class="section-header">
                  <span class="section-title">表达风格</span>
                  <span class="section-tip">（不选择使用默认风格）</span>
                </div>
                <a-radio-group v-model:value="selectedStyle" class="style-group">
                  <a-radio value="">默认</a-radio>
                  <a-radio value="tech">科技风格</a-radio>
                  <a-radio value="emotional">情感风格</a-radio>
                  <a-radio value="educational">教育风格</a-radio>
                  <a-radio value="humorous">轻松幽默</a-radio>
                </a-radio-group>
              </div>

              <!-- 配图方式选择 -->
              <div class="image-methods-section">
                <div class="section-header">
                  <span class="section-title">配图方式</span>
                  <span class="section-tip">（不选择表示支持所有方式）</span>
                </div>
                <a-checkbox-group v-model:value="selectedImageMethods" class="methods-group">
                  <a-checkbox value="PEXELS">Pexels</a-checkbox>
                  <a-checkbox value="MERMAID">Mermaid</a-checkbox>
                  <a-checkbox value="ICONIFY">Iconify</a-checkbox>
                  <a-checkbox value="MEME">表情包</a-checkbox>
                  <a-checkbox value="SVG_DIAGRAM">SVG</a-checkbox>
                </a-checkbox-group>
              </div>

              <a-button
                type="primary"
                size="large"
                :loading="isCreating"
                :disabled="!topic.trim()"
                @click="startCreate"
                class="create-btn"
              >
                <template #icon>
                  <RocketOutlined />
                </template>
                开始创作
              </a-button>
            </div>
          </div>
          </div>

          <!-- 标题生成中 -->
          <div v-else-if="currentPhase === 'TITLE_GENERATING'" key="title-generating" class="loading-stage">
            <a-spin size="large" />
            <h3>AI 正在生成标题方案...</h3>
            <p>稍等片刻，即将为您呈现多个精彩标题</p>
          </div>

          <!-- 标题选择阶段 -->
          <TitleSelectingStage
            v-else-if="currentPhase === 'TITLE_SELECTING'"
            key="title-selecting"
            :title-options="titleOptions"
            :loading="confirmLoading"
            @confirm="handleConfirmTitle"
          />

          <!-- 大纲生成中（流式展示） -->
          <div v-else-if="currentPhase === 'OUTLINE_GENERATING'" key="outline-generating" class="outline-generating-state">
            <!-- 标题预览 -->
            <div v-if="article.mainTitle" class="preview-header">
              <h1 class="article-title">{{ article.mainTitle }}</h1>
              <p class="article-subtitle">{{ article.subTitle }}</p>
            </div>

            <!-- 大纲结果在生成完成后切换到可编辑状态 -->
            <div class="outline-preview">
              <div class="section-label">
                <BulbOutlined />
                <span>AI 正在规划文章大纲</span>
                <span class="typing-cursor">|</span>
              </div>
              <div class="outline-loading">
                <a-spin />
                <span>{{ activeAgentProgress?.summary || '正在构建文章结构...' }}</span>
              </div>
            </div>
          </div>

          <!-- 大纲编辑阶段 -->
          <OutlineEditingStage
            v-else-if="currentPhase === 'OUTLINE_EDITING'"
            key="outline-editing"
            :outline="outline"
            :loading="confirmLoading"
            :task-id="taskId"
            @confirm="handleConfirmOutline"
          />

          <!-- 正文生成阶段 -->
          <div v-else-if="currentPhase === 'CONTENT_GENERATING'" key="content-generating" class="creating-state">
          <!-- 标题预览 -->
          <div v-if="article.mainTitle" class="preview-header">
            <h1 class="article-title">{{ article.mainTitle }}</h1>
            <p class="article-subtitle">{{ article.subTitle }}</p>
          </div>

          <!-- 大纲预览（流式解析展示） -->
          <div v-if="outlineRaw" class="outline-preview">
            <div class="section-label">
              <BulbOutlined />
              <span>文章大纲</span>
              <span v-if="isOutlineStreaming" class="typing-cursor">|</span>
            </div>
            <div class="outline-list">
              <div
                v-for="item in parsedOutline"
                :key="item.section"
                class="outline-item"
              >
                <div class="outline-title">{{ item.section }}. {{ item.title }}</div>
                <ul class="outline-points">
                  <li v-for="(point, idx) in item.points" :key="idx">{{ point }}</li>
                </ul>
              </div>
            </div>
          </div>

          <!-- 正文在生成过程中实时展示，不再只显示摘要 -->
          <div v-if="article.content" class="content-preview live-content-preview">
            <div class="live-content-heading">
              <FileTextOutlined />
              <span>正文实时生成</span>
              <span v-if="currentStep === 2" class="typing-cursor">|</span>
            </div>
            <div v-html="markdownToHtml(article.content)" class="markdown-body"></div>
          </div>
          <div v-else-if="currentStep === 2" class="outline-loading content-generating-placeholder">
            <a-spin />
            <span>{{ activeAgentProgress?.summary || '正在撰写正文...' }}</span>
          </div>

          <!-- 配图进度 -->
          <div v-if="currentStep === 4 && imageProgress > 0" class="image-progress-box">
            <div class="progress-header">
              <PictureOutlined />
              <span>正在生成配图</span>
            </div>
            <a-progress :percent="imageProgress" status="active" :stroke-color="{ from: '#22C55E', to: '#16A34A' }" />
            <p class="progress-hint">{{ imageCount }}/{{ totalImages }} 张图片已完成</p>
          </div>

          <!-- 加载占位 -->
          <div v-if="currentStep === 0 && !article.mainTitle" class="loading-placeholder">
            <a-spin size="large" />
            <p>AI 正在构思标题...</p>
          </div>
          </div>

          <!-- 创作完成 -->
          <div v-else-if="currentPhase === 'COMPLETED'" key="completed" class="completed-state">
          <div class="success-header">
            <CheckCircleFilled class="success-icon" />
            <span>文章创作完成！</span>
          </div>

          <div class="preview-header">
            <h1 class="article-title">{{ article.mainTitle }}</h1>
            <p class="article-subtitle">{{ article.subTitle }}</p>
          </div>
          <div class="content-preview">
            <div v-html="markdownToHtml(article.fullContent || article.content || '')" class="markdown-body"></div>
          </div>
          </div>
        </Transition>
      </main>

      <!-- 右侧：辅助面板 -->
      <aside class="sidebar-right">
        <!-- 热门选题 -->
        <div v-if="currentPhase === 'INPUT'" class="panel-section">
          <h4 class="panel-title">
            <BulbOutlined />
            热门选题
          </h4>
          <div class="hot-tags">
            <span
              v-for="example in exampleTopics"
              :key="example"
              class="hot-tag"
              @click="topic = example"
            >
              {{ example }}
            </span>
          </div>
        </div>

        <!-- 创作技巧 -->
        <div v-if="currentPhase === 'INPUT'" class="panel-section">
          <h4 class="panel-title">
            <StarOutlined />
            营销技巧
          </h4>
          <div class="tips-list">
            <div class="tip-item">
              <div class="tip-icon">1</div>
              <div class="tip-content">
                <div class="tip-title">明确受众</div>
                <div class="tip-desc">先想清楚这条内容写给谁看</div>
              </div>
            </div>
            <div class="tip-item">
              <div class="tip-icon">2</div>
              <div class="tip-content">
                <div class="tip-title">突出卖点</div>
                <div class="tip-desc">把产品价值讲具体，别只喊口号</div>
              </div>
            </div>
            <div class="tip-item">
              <div class="tip-icon">3</div>
              <div class="tip-content">
                <div class="tip-title">贴合平台</div>
                <div class="tip-desc">按渠道规则和内容形式调整表达</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 创作进行中的提示（所有创作阶段） -->
        <div v-if="isCreating || currentPhase === 'TITLE_SELECTING' || currentPhase === 'OUTLINE_EDITING'" class="panel-section">
          <h4 class="panel-title">
            <ClockCircleOutlined />
            创作进度
          </h4>
          <div class="progress-info">
            <div class="progress-step">
              <span class="step-label">当前步骤</span>
              <span class="step-value">{{ agentSteps[currentStep]?.title }}</span>
            </div>
            <div class="progress-step">
              <span class="step-label">已完成</span>
              <span class="step-value">{{ currentStep }}/{{ agentSteps.length }}</span>
            </div>
          </div>
          <div v-if="isCreating" class="progress-tip">
            <InfoCircleOutlined />
            <span>AI 正在努力创作中，请耐心等待...</span>
          </div>
          <div v-else class="progress-tip waiting">
            <InfoCircleOutlined />
            <span>等待您的确认...</span>
          </div>
        </div>

        <!-- 当前选题提示 -->
        <div v-if="currentPhase !== 'INPUT' && currentPhase !== 'COMPLETED' && topic" class="panel-section">
          <h4 class="panel-title">
            <BulbOutlined />
            创作选题
          </h4>
          <div class="topic-display">
            <p>{{ topic }}</p>
          </div>
        </div>

        <!-- 阶段提示 -->
        <div v-if="currentPhase === 'TITLE_GENERATING'" class="panel-section tips-section">
          <h4 class="panel-title">
            <StarOutlined />
            提示
          </h4>
          <div class="tips-list">
            <div class="tip-item">
              <div class="tip-icon">💡</div>
              <div class="tip-content">
                <div class="tip-desc">AI 正在分析您的选题，生成多个吸引眼球的标题方案</div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="currentPhase === 'TITLE_SELECTING'" class="panel-section tips-section">
          <h4 class="panel-title">
            <StarOutlined />
            提示
          </h4>
          <div class="tips-list">
            <div class="tip-item">
              <div class="tip-icon">✅</div>
              <div class="tip-content">
                <div class="tip-desc">选择最符合您期望的标题，或添加补充描述让 AI 更好地理解您的需求</div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="currentPhase === 'OUTLINE_GENERATING'" class="panel-section tips-section">
          <h4 class="panel-title">
            <StarOutlined />
            提示
          </h4>
          <div class="tips-list">
            <div class="tip-item">
              <div class="tip-icon">📝</div>
              <div class="tip-content">
                <div class="tip-desc">AI 正在为您规划文章结构，构建清晰的章节脉络</div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="currentPhase === 'OUTLINE_EDITING'" class="panel-section tips-section">
          <h4 class="panel-title">
            <StarOutlined />
            编辑技巧
          </h4>
          <div class="tips-list">
            <div class="tip-item">
              <div class="tip-icon">1</div>
              <div class="tip-content">
                <div class="tip-title">拖动排序</div>
                <div class="tip-desc">点击章节左侧拖动图标可调整章节顺序</div>
              </div>
            </div>
            <div class="tip-item">
              <div class="tip-icon">2</div>
              <div class="tip-content">
                <div class="tip-title">AI 助手</div>
                <div class="tip-desc">使用 AI 助手快速修改大纲结构</div>
              </div>
            </div>
            <div class="tip-item">
              <div class="tip-icon">3</div>
              <div class="tip-content">
                <div class="tip-title">添加章节</div>
                <div class="tip-desc">根据需要添加或删除章节和要点</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div v-if="currentPhase === 'COMPLETED'" class="panel-section">
          <h4 class="panel-title">
            <ThunderboltOutlined />
            快捷操作
          </h4>
          <div class="action-list">
            <a-button block @click="copyContent" class="action-btn">
              <CopyOutlined />
              复制全文
            </a-button>
            <a-button block @click="viewArticle" class="action-btn">
              <EyeOutlined />
              查看详情
            </a-button>
            <a-button block type="primary" @click="resetCreate" class="action-btn primary">
              <RedoOutlined />
              再创作一篇
            </a-button>
          </div>
        </div>

        <!-- 完成后的统计 -->
        <div v-if="currentPhase === 'COMPLETED'" class="panel-section stats-section">
          <h4 class="panel-title">
            <BarChartOutlined />
            文章统计
          </h4>
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-value">{{ (article.fullContent || article.content || '').length }}</div>
              <div class="stat-label">字数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ article.images?.length || 0 }}</div>
              <div class="stat-label">配图</div>
            </div>
          </div>
        </div>

        <!-- 底部帮助链接 -->
        <div class="panel-footer">
          <a class="help-link">
            <QuestionCircleOutlined />
            使用帮助
          </a>
          <a class="help-link">
            <MessageOutlined />
            反馈建议
          </a>
        </div>
      </aside>
    </div>

    <!-- 错误提示 -->
    <a-modal
      v-model:open="errorVisible"
      title="创作失败"
      @ok="errorVisible = false"
    >
      <p>{{ errorMessage }}</p>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount, onMounted, watch, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { useLoginUserStore } from '@/stores/loginUser'
import {
  RocketOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  CheckCircleFilled,
  CloseCircleOutlined,
  CopyOutlined,
  EyeOutlined,
  RedoOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  StarOutlined,
  ClockCircleOutlined,
  InfoCircleOutlined,
  BarChartOutlined,
  QuestionCircleOutlined,
  MessageOutlined,
  PictureOutlined,
  FileTextOutlined
} from '@ant-design/icons-vue'
import { createArticle, confirmTitle, confirmOutline } from '@/api/articleController'
import { connectSSE, closeSSE, type SSEMessage } from '@/utils/sse'
import { markdownToHtml } from '@/utils/markdown'
import { getMarketingPlatforms, getProductProfiles, type MarketingPlatform, type ProductProfile } from '@/api/marketingController'
import TitleSelectingStage from './components/TitleSelectingStage.vue'
import OutlineEditingStage from './components/OutlineEditingStage.vue'

const router = useRouter()
const route = useRoute()
const loginUserStore = useLoginUserStore()

// 智能体步骤（对应后端 6 个步骤）
const agentSteps = [
  { title: '生成标题', description: 'AI 分析选题，生成吸睛标题' },
  { title: '规划大纲', description: '构建文章结构，理清脉络' },
  { title: '撰写正文', description: '流式生成高质量文章内容' },
  { title: '分析配图', description: '智能分析配图需求和位置' },
  { title: '生成配图', description: '自动匹配高清无版权图片' },
  { title: '图文合成', description: '将配图插入正文，完美呈现' },
]
const agentStepIndexes: Record<string, number> = {
  agent1_generate_titles: 0,
  agent2_generate_outline: 1,
  agent3_generate_content: 2,
  agent4_analyze_image_requirements: 3,
  agent5_generate_images: 4,
  agent6_merge_content: 5,
}

// 示例选题
const exampleTopics = [
  '新品上市小红书种草笔记',
  '公众号产品深度推文',
  '抖音短视频口播脚本',
  '618 大促活动预热文案',
  '私域社群转化话术',
  '用户好评整理成笔记',
]

// 阶段状态
const currentPhase = ref<string>('INPUT')  // INPUT, TITLE_SELECTING, OUTLINE_EDITING, CONTENT_GENERATING, COMPLETED

// 状态
const topic = ref('')
const selectedStyle = ref('')  // 选中的文章风格（空字符串表示默认）
const selectedImageMethods = ref<string[]>([])  // 选中的配图方式（空数组表示全部）
const platforms = ref<MarketingPlatform[]>([])
const products = ref<ProductProfile[]>([])
const selectedPlatformId = ref<number>()
const selectedProductId = ref<number>()
const selectedPlatform = computed(() => platforms.value.find((platform) => platform.id === selectedPlatformId.value))
const isCreating = ref(false)
const isOutlineStreaming = ref(false)
const currentStep = ref(0)
const taskId = ref('')
const errorVisible = ref(false)
const errorMessage = ref('')
const confirmLoading = ref(false)
const processExpanded = ref(false)
const logsContainerRef = ref<HTMLElement | null>(null)
const activeToolCall = ref<{ name: string, label: string, query: string } | null>(null)
const activeAgentProgress = ref<{
  agent: string
  title: string
  status: 'started' | 'completed' | 'failed'
  summary: string
} | null>(null)

// 实时日志
interface RealtimeLog {
  id: number
  timestamp: number
  level: string
  message: string
  kind?: 'progress' | 'reasoning' | 'tool' | 'activity' | 'meme-result'
  status?: 'running' | 'completed' | 'failed'
  memeItems?: Array<{ memeId: string, imageUrl: string }>
}
const realtimeLogs = ref<RealtimeLog[]>([])
let logSequence = 0
const toolLabels: Record<string, string> = {
  search_internet: '搜索互联网',
  search_images: '搜索图片',
  search_memes: '搜索表情包',
  search_database: '搜索资料库',
  get_marketing_performance: '读取营销效果数据',
}

// 标题方案
const titleOptions = ref<Array<{mainTitle: string, subTitle: string}>>([])

// 大纲数据
const outline = ref<Array<{section: number, title: string, points: string[]}>>([])

// 大纲数据（流式）
const outlineRaw = ref('')

// 大纲项类型
interface OutlineItem {
  title: string
  points: string[]
  section: number
}

// 解析大纲 JSON（格式为 { "sections": [...] }）
const parsedOutline = computed<OutlineItem[]>(() => {
  if (!outlineRaw.value) return []

  const str = outlineRaw.value.trim()

  // 尝试解析完整的 JSON
  try {
    const parsed = JSON.parse(str)
    if (parsed && Array.isArray(parsed.sections)) {
      return parsed.sections
    }
    return []
  } catch {
    // JSON 不完整时，尝试解析已完成的部分
    try {
      // 找到最后一个完整的 section 对象 }
      // 格式: { "sections": [ {...}, {...} ] }
      const sectionsMatch = str.match(/"sections"\s*:\s*\[/)
      if (!sectionsMatch) return []

      const sectionsStart = str.indexOf('[', sectionsMatch.index)
      if (sectionsStart === -1) return []

      // 从 sections 数组开始，找到最后一个完整的 }
      const afterStart = str.substring(sectionsStart)
      const lastBrace = afterStart.lastIndexOf('}')

      if (lastBrace > 0) {
        const partialArray = afterStart.substring(0, lastBrace + 1) + ']'
        const parsed = JSON.parse(partialArray)
        if (Array.isArray(parsed)) {
          return parsed
        }
      }
      return []
    } catch {
      return []
    }
  }
})

// 配图进度
const imageCount = ref(0)
const totalImages = ref(0)
const imageProgress = computed(() => totalImages.value > 0
  ? Math.round((imageCount.value / totalImages.value) * 100)
  : 0)

// 文章数据
const article = ref<Partial<API.ArticleVO>>({
  mainTitle: '',
  subTitle: '',
  content: '',
  fullContent: '',
  images: [],
})

let eventSource: EventSource | null = null

// 开始创作
const startCreate = async () => {
  if (!topic.value.trim()) {
    message.warning('请输入选题')
    return
  }
  if (!selectedPlatformId.value) {
    message.warning('请选择发布平台')
    return
  }

  isCreating.value = true
  currentStep.value = 0
  clearReasoningBuffer()
  realtimeLogs.value = []
  logSequence = 0
  activeToolCall.value = null
  activeAgentProgress.value = null
  processExpanded.value = true
  addLog('开始创建文章任务...', 'info')

  try {
    // 创建任务
    const res = await createArticle({
      topic: topic.value,
      style: selectedStyle.value || undefined,
      platformId: selectedPlatformId.value,
      productId: selectedProductId.value,
      enabledImageMethods: selectedImageMethods.value.length > 0 ? selectedImageMethods.value : undefined
    })
    const newTaskId = res.data.data
    if (!newTaskId) {
      throw new Error('创建任务失败：未返回任务ID')
    }
    taskId.value = newTaskId
    addLog(`任务创建成功，ID: ${newTaskId}`, 'success')

    // 刷新用户信息（更新配额）
    await loginUserStore.fetchLoginUser()

    // 建立 SSE 连接
    addLog('已建立实时连接，开始生成...', 'info')
    eventSource = connectSSE(taskId.value, {
      onMessage: handleSSEMessage,
      onError: handleSSEError,
      onComplete: handleSSEComplete,
    })
  } catch (error) {
    const err = error as Error
    message.error(err.message || '创建任务失败')
    isCreating.value = false
  }
}

// 添加日志
const addLog = (
  message: string,
  level: string = 'info',
  kind: RealtimeLog['kind'] = 'activity',
  status?: RealtimeLog['status'],
) => {
  realtimeLogs.value.push({
    id: ++logSequence,
    timestamp: Date.now(),
    level,
    message,
    kind,
    status,
  })
}

// 高频 token 先缓冲，避免每次接收都触发 Vue 渲染和日志布局。
const REASONING_REFRESH_INTERVAL_MS = 100
let pendingReasoning = ''
let reasoningTimer: ReturnType<typeof setTimeout> | undefined

const clearReasoningBuffer = () => {
  clearTimeout(reasoningTimer)
  reasoningTimer = undefined
  pendingReasoning = ''
}

const flushReasoning = () => {
  clearTimeout(reasoningTimer)
  reasoningTimer = undefined
  if (!pendingReasoning) return

  const content = pendingReasoning
  pendingReasoning = ''
  const lastLog = realtimeLogs.value[realtimeLogs.value.length - 1]
  if (lastLog?.kind === 'reasoning') {
    lastLog.message += content
  } else {
    addLog(content, 'info', 'reasoning')
  }
  processExpanded.value = true
}

const appendReasoning = (content: string) => {
  if (!content) return
  pendingReasoning += content
  if (reasoningTimer === undefined) {
    reasoningTimer = setTimeout(flushReasoning, REASONING_REFRESH_INTERVAL_MS)
  }
}

// DOM 更新后统一滚动，覆盖新增日志、推理追加和展开面板。
watch(
  () => [realtimeLogs.value.length, realtimeLogs.value[realtimeLogs.value.length - 1]?.message, processExpanded.value],
  () => {
    const container = logsContainerRef.value
    container?.scrollTo({ top: container.scrollHeight })
  },
  { flush: 'post' },
)

// 格式化日志时间
const formatLogTime = (timestamp: number) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

// 处理 SSE 消息
const handleSSEMessage = (msg: SSEMessage) => {
  // 先写入前面的推理，保持步骤、工具事件与推理的先后顺序。
  if (msg.type !== 'AGENT_REASONING_STREAMING') flushReasoning()
  switch (msg.type) {
    case 'AGENT_PROGRESS': {
      const status: 'started' | 'completed' | 'failed' = msg.status === 'completed'
        ? 'completed'
        : msg.status === 'failed'
          ? 'failed'
          : 'started'
      const progress = {
        agent: msg.agent || '',
        title: msg.title || 'AI 处理',
        status,
        summary: msg.summary || '',
      }
      activeAgentProgress.value = progress
      processExpanded.value = true
      if (status === 'started') {
        currentStep.value = agentStepIndexes[msg.agent] ?? currentStep.value
        currentPhase.value = msg.agent === 'agent1_generate_titles'
          ? 'TITLE_GENERATING'
          : msg.agent === 'agent2_generate_outline'
            ? 'OUTLINE_GENERATING'
            : 'CONTENT_GENERATING'
        isCreating.value = true
      }
      addLog(
        `${status === 'started' ? '开始' : '完成'}${progress.title}：${progress.summary}`,
        status === 'started' ? 'info' : 'success',
        'progress',
      )
      break
    }

    case 'AGENT_REASONING_STREAMING':
      appendReasoning(msg.content || '')
      break

    case 'AGENT1_COMPLETE':
      // 智能体1完成，进入标题生成阶段（显示加载）
      currentPhase.value = 'TITLE_GENERATING'
      currentStep.value = 1
      addLog('智能体1：标题方案生成完成', 'success')
      break

    case 'TITLES_GENERATED':
      // 标题方案生成完成，切换到选择标题阶段
      currentPhase.value = 'TITLE_SELECTING'
      titleOptions.value = msg.titleOptions || []
      isCreating.value = false
      addLog(`生成了 ${msg.titleOptions?.length || 0} 个标题方案`, 'success')
      break

    case 'AGENT2_STREAMING':
      // 大纲流式输出（显示生成中状态）
      currentPhase.value = 'OUTLINE_GENERATING'
      isOutlineStreaming.value = true
      outlineRaw.value += msg.content || ''
      break

    case 'OUTLINE_GENERATED':
      // 大纲生成完成，切换到编辑大纲阶段
      currentPhase.value = 'OUTLINE_EDITING'
      outline.value = msg.outline || []
      isCreating.value = false
      isOutlineStreaming.value = false
      addLog('大纲生成完成，等待确认', 'success')
      // 保持在步骤1（规划大纲），用户编辑大纲时仍处于此阶段
      break

    case 'AGENT2_COMPLETE':
      // 大纲完成（内部处理，已在 OUTLINE_GENERATED 中切换阶段）
      // 不改变 currentStep，保持在步骤1，等用户确认大纲后才进入步骤2
      break

    case 'AGENT3_STREAMING':
      // 正文流式输出，进入步骤2（撰写正文）
      currentPhase.value = 'CONTENT_GENERATING'
      currentStep.value = 2
      article.value.content += msg.content || ''
      break

    case 'AGENT3_COMPLETE':
      // 正文完成，进入配图分析步骤
      currentStep.value = 3
      addLog('正文生成完成', 'success')
      break

    case 'TOOL_CALL': {
      const toolName = toolLabels[msg.name] || msg.name || '未知工具'
      const rawQuery = msg.arguments?.query
      const query = typeof rawQuery === 'string' ? rawQuery.trim() : ''
      const queryText = query ? `：${query.length > 120 ? `${query.slice(0, 120)}…` : query}` : ''
      if (msg.status === 'running') {
        processExpanded.value = true
        activeToolCall.value = { name: msg.name || '', label: toolName, query: queryText.slice(1) }
        addLog(`正在调用${toolName}${queryText}`, 'info', 'tool', 'running')
      } else if (msg.status === 'completed') {
        activeToolCall.value = null
        addLog(`${toolName}调用完成`, 'success', 'tool', 'completed')
        if (msg.result?.type === 'MEME_SEARCH_RESULT') {
          const items = Array.isArray(msg.result.items)
            ? msg.result.items.filter(
              (item: any) => typeof item?.memeId === 'string' && typeof item?.imageUrl === 'string',
            )
            : []
          addLog(
            `已返回 ${items.length} 张候选图，后续将使用 memeId 回填配图需求`,
            'info',
            'meme-result',
          )
          realtimeLogs.value[realtimeLogs.value.length - 1].memeItems = items
        }
      } else {
        activeToolCall.value = null
        addLog(`${toolName}调用失败`, 'error', 'tool', 'failed')
      }
      break
    }

    case 'AGENT4_COMPLETE':
      // 配图分析完成，进入配图生成步骤
      currentStep.value = 4
      totalImages.value = msg.imageRequirements?.length ?? 0
      addLog(`配图需求分析完成，共 ${totalImages.value} 张`, 'success')
      break

    case 'IMAGE_COMPLETE':
      // 单张配图完成
      imageCount.value++
      addLog(`配图生成中 ${imageCount.value}/${totalImages.value}`, 'info')
      break

    case 'AGENT5_COMPLETE':
      // 所有配图完成，进入图文合成步骤
      currentStep.value = 5
      article.value.images = msg.images
      addLog('所有配图生成完成', 'success')
      break

    case 'MERGE_COMPLETE':
      // 图文合成完成
      article.value.fullContent = msg.fullContent
      addLog('图文合成完成', 'success')
      break

    case 'ALL_COMPLETE':
      // 全部完成
      currentPhase.value = 'COMPLETED'
      currentStep.value = 6
      isCreating.value = false
      activeToolCall.value = null
      processExpanded.value = true
      message.success('文章创作完成!')
      addLog('✨ 文章创作完成！', 'success')
      break

    case 'ERROR':
      errorMessage.value = msg.message || '创作失败'
      errorVisible.value = true
      isCreating.value = false
      currentPhase.value = 'INPUT'
      if (activeAgentProgress.value?.status === 'started') {
        activeAgentProgress.value.status = 'failed'
        activeAgentProgress.value.summary = errorMessage.value
      }
      activeToolCall.value = null
      processExpanded.value = true
      addLog(`创作失败: ${msg.message || '未知错误'}`, 'error')
      break
  }
}

// 确认标题
const handleConfirmTitle = async (data: {mainTitle: string, subTitle: string, userDescription: string}) => {
  confirmLoading.value = true
  try {
    await confirmTitle({
      taskId: taskId.value,
      selectedMainTitle: data.mainTitle,
      selectedSubTitle: data.subTitle,
      userDescription: data.userDescription
    })
    // 保存标题信息，用于大纲生成阶段展示
    article.value.mainTitle = data.mainTitle
    article.value.subTitle = data.subTitle
    // 不直接切换阶段，等待 SSE 消息 OUTLINE_GENERATED
    message.success('标题已确认，正在生成大纲...')
  } catch (error) {
    const err = error as Error
    message.error(err.message || '确认标题失败')
  } finally {
    confirmLoading.value = false
  }
}

// 确认大纲
const handleConfirmOutline = async (outlineData: Array<{section: number, title: string, points: string[]}>) => {
  confirmLoading.value = true
  try {
    await confirmOutline({
      taskId: taskId.value,
      outline: outlineData
    })
    // 更新 outlineRaw 为用户修改后的大纲，确保 CONTENT_GENERATING 阶段展示正确的大纲
    outlineRaw.value = JSON.stringify({ sections: outlineData })
    // 不直接切换阶段，等待后端开始生成正文并推送 AGENT3_STREAMING
    message.success('大纲已确认，正在生成正文...')
  } catch (error) {
    const err = error as Error
    message.error(err.message || '确认大纲失败')
  } finally {
    confirmLoading.value = false
  }
}

// 处理 SSE 错误
const handleSSEError = (error: Event) => {
  flushReasoning()
  console.error('SSE错误:', error)
  message.error('连接失败,请重试')
  isCreating.value = false
}

// 处理 SSE 完成
const handleSSEComplete = () => {
  console.log('SSE连接关闭')
}

// 复制全文
const copyContent = async () => {
  const content = article.value.fullContent || article.value.content || ''
  try {
    await navigator.clipboard.writeText(content)
    message.success('已复制到剪贴板')
  } catch {
    message.error('复制失败')
  }
}

// 查看文章详情
const viewArticle = () => {
  router.push(`/article/${taskId.value}`)
}

// 重新创作
const resetCreate = () => {
  currentPhase.value = 'INPUT'
  topic.value = ''
  selectedStyle.value = ''
  titleOptions.value = []
  outline.value = []
  isCreating.value = false
  isOutlineStreaming.value = false
  processExpanded.value = false
  activeToolCall.value = null
  activeAgentProgress.value = null
  currentStep.value = 0
  imageCount.value = 0
  outlineRaw.value = ''
  confirmLoading.value = false
  clearReasoningBuffer()
  realtimeLogs.value = []
  logSequence = 0
  article.value = {
    mainTitle: '',
    subTitle: '',
    content: '',
    fullContent: '',
    images: [],
  }
}

// 组件挂载时检查路由参数
onMounted(async () => {
  if (route.query.topic) {
    topic.value = route.query.topic as string
  }
  try {
    const [platformResponse, productResponse] = await Promise.all([
      getMarketingPlatforms(),
      getProductProfiles(),
    ])
    if (platformResponse.data.code === 0) {
      platforms.value = platformResponse.data.data || []
      selectedPlatformId.value = platforms.value[0]?.id
    }
    if (productResponse.data.code === 0) products.value = productResponse.data.data || []
  } catch (error) {
    message.error((error as Error).message || '加载营销资料失败')
  }
})

// 组件卸载前关闭 SSE
onBeforeUnmount(() => {
  clearReasoningBuffer()
  closeSSE(eventSource)
})
</script>

<style scoped lang="scss">
.article-create-page {
  height: calc(100vh - 64px);
  background: var(--color-background-secondary);
  overflow: hidden;
}

.create-layout {
  display: grid;
  grid-template-columns: 320px 1fr 300px;
  height: 100%;
}

/* 左侧边栏 */
.sidebar-left {
  background: white;
  border-right: 1px solid var(--color-border);
  padding: 24px;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.sidebar-header {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--color-border-light);
}

.sidebar-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 4px;
  color: var(--color-text);
}

.sidebar-subtitle {
  font-size: 13px;
  color: var(--color-text-muted);
  margin: 0;
}

.flow-timeline {
  flex: 1;
}

.flow-item {
  display: flex;
  gap: 14px;
  padding: 14px 0;
  position: relative;

  &:not(:last-child)::before {
    content: '';
    position: absolute;
    left: 15px;
    top: 46px;
    bottom: -14px;
    width: 2px;
    background: var(--color-border);
  }

  &.completed::before {
    background: var(--color-primary);
  }

  &.active::before {
    background: linear-gradient(180deg, var(--color-primary) 50%, var(--color-border) 50%);
  }
}

.flow-indicator {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 14px;
  transition: all var(--transition-normal);

  .pending & {
    background: var(--color-background-tertiary);
    color: var(--color-text-muted);
    border: 2px solid var(--color-border);
  }

  .active & {
    background: rgba(34, 197, 94, 0.1);
    color: var(--color-primary);
    border: 2px solid var(--color-primary);
  }

  .completed & {
    background: var(--color-primary);
    color: white;
  }

  .step-number {
    font-weight: 600;
  }

  .spin-icon {
    animation: spin 1s linear infinite;
  }
}

.flow-content {
  flex: 1;
  min-width: 0;
}

.flow-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 2px;

  .pending & {
    color: var(--color-text-muted);
  }

  .active & {
    color: var(--color-primary-dark);
  }
}

.flow-desc {
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.4;
}

.flow-status {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-primary);
  font-weight: 500;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  animation: pulse 1.5s infinite;
}


/* 主内容区 */
.main-content {
  padding: 28px clamp(24px, 4vw, 64px) 48px;
  overflow-y: auto;
  background: #f7faf8;
}

/* 输入状态 */
.input-state {
  max-width: 700px;
  margin: 0 auto;
  padding-top: 60px;
}

.input-card {
  background: var(--color-background-secondary);
  border-radius: var(--radius-xl);
  padding: 40px;
}

.input-header {
  text-align: center;
  margin-bottom: 32px;
}

.input-title {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 8px;
  color: var(--color-text);
}

.input-subtitle {
  font-size: 15px;
  color: var(--color-text-secondary);
  margin: 0;
}

.input-area {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.topic-textarea {
  font-size: 15px;
  border-radius: var(--radius-lg);
  padding: 16px;
  background: white;

  &:focus {
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.1);
  }
}

.create-btn.ant-btn {
  height: 52px;
  font-size: 16px;
  font-weight: 600;
  border-radius: var(--radius-lg);
  background: var(--gradient-primary) !important;
  border: none !important;
  color: white !important;
  box-shadow: 0 4px 14px rgba(34, 197, 94, 0.3) !important;

  &:hover,
  &:focus,
  &:active {
    background: var(--gradient-primary) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 4px 14px rgba(34, 197, 94, 0.3) !important;
    opacity: 0.92;
  }

  &:disabled,
  &.ant-btn-disabled {
    background: var(--color-border) !important;
    box-shadow: none !important;
    opacity: 0.6;
    color: var(--color-text-muted) !important;
  }
}

/* 文章风格选择 */
.style-section {
  padding: 16px;
  background: var(--color-background-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
}

.context-select-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.context-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: var(--color-text);
  font-size: 13px;
  font-weight: 600;
}

.context-field i {
  margin-left: 5px;
  color: var(--color-text-muted);
  font-size: 11px;
  font-style: normal;
  font-weight: 400;
}

.context-hint {
  margin-top: -8px;
  color: var(--color-primary-dark);
  font-size: 12px;
  line-height: 1.6;
}

.context-hint span {
  margin-left: 5px;
  color: var(--color-text-muted);
}

.style-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.style-group :deep(.ant-radio-wrapper) {
  margin: 0;
  padding: 6px 12px;
  background: white;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all 0.2s;
}

.style-group :deep(.ant-radio-wrapper:hover) {
  border-color: var(--color-primary);
  background: rgba(34, 197, 94, 0.04);
}

.style-group :deep(.ant-radio-wrapper-checked) {
  border-color: var(--color-primary);
  background: rgba(34, 197, 94, 0.08);
}

/* 配图方式选择 */
.image-methods-section {
  padding: 16px;
  background: var(--color-background-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
}

.section-tip {
  font-size: 12px;
  color: var(--color-text-muted);
}

.methods-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.methods-group :deep(.ant-checkbox-wrapper) {
  margin: 0;
  padding: 6px 12px;
  background: white;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all 0.2s;
}

.methods-group :deep(.ant-checkbox-wrapper:hover) {
  border-color: var(--color-primary);
  background: rgba(34, 197, 94, 0.04);
}

.methods-group :deep(.ant-checkbox-wrapper-checked) {
  border-color: var(--color-primary);
  background: rgba(34, 197, 94, 0.08);
}

.methods-group :deep(.ant-checkbox-wrapper-disabled) {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 创作进行中 */
.creating-state,
.completed-state {
  max-width: 100%;
}

/* 标题区域 */
.preview-header {
  text-align: center;
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--color-border-light);
}

.article-title {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 8px;
  color: var(--color-text);
  line-height: 1.4;
}

.article-subtitle {
  font-size: 16px;
  color: var(--color-text-secondary);
  margin: 0;
}

/* 大纲预览 */
.outline-preview {
  margin-bottom: 24px;
  padding: 20px 24px;
  background: var(--color-background-secondary);
  border-radius: var(--radius-lg);
}

.section-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: 16px;
}

.outline-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.outline-item {
  padding: 12px 16px;
  background: white;
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-primary);
}

.outline-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 8px;
}

.outline-points {
  margin: 0;
  padding-left: 18px;

  li {
    font-size: 13px;
    color: var(--color-text-secondary);
    line-height: 1.6;
    margin-bottom: 4px;

    &:last-child {
      margin-bottom: 0;
    }
  }
}

/* 正文预览 */
.content-preview {
  line-height: 1.8;
}

.live-content-preview {
  margin-top: 24px;
  padding: 24px clamp(20px, 3vw, 40px);
  background: white;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
}

.live-content-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 18px;
  color: var(--color-primary-dark);
  font-size: 13px;
  font-weight: 600;
}

.markdown-body {
  line-height: 1.8;
  font-size: 15px;
  color: var(--color-text);

  :deep(h2) {
    font-size: 20px;
    font-weight: 600;
    margin: 24px 0 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--color-border);
    color: var(--color-text);
  }

  :deep(p) {
    margin-bottom: 14px;
    text-indent: 2em;
  }

  :deep(img) {
    display: block;
    max-width: 100%;
    max-height: 600px;
    width: auto;
    height: auto;
    margin: 20px auto;
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
    object-fit: contain;
  }

  // Mermaid 图表特殊处理（SVG 格式）
  :deep(img[src$=".svg"]) {
    max-width: 800px;
    max-height: 500px;
  }
}

.typing-cursor {
  display: inline-block;
  animation: blink 1s infinite;
  color: var(--color-primary);
  font-weight: bold;
  font-size: 18px;
}

.image-progress-box {
  background: var(--color-background-secondary);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-top: 24px;
  text-align: center;

  .progress-header {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-bottom: 16px;
    font-size: 15px;
    font-weight: 600;
    color: var(--color-text);
  }

  .progress-hint {
    margin: 12px 0 0;
    font-size: 13px;
    color: var(--color-text-muted);
  }
}

.loading-placeholder {
  text-align: center;
  padding: 100px 0;

  p {
    margin: 16px 0 0;
    color: var(--color-text-secondary);
    font-size: 15px;
  }
}

/* 完成状态 */
.success-header {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--gradient-primary);
  border-radius: var(--radius-full);
  margin-bottom: 24px;
  color: white;
  font-size: 14px;
  font-weight: 600;

  .success-icon {
    font-size: 16px;
  }
}

/* 右侧辅助面板 */
.sidebar-right {
  background: white;
  border-left: 1px solid var(--color-border);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
}

.panel-section {
  padding-bottom: 20px;
  border-bottom: 1px solid var(--color-border-light);

  &:last-of-type {
    border-bottom: none;
    padding-bottom: 0;
  }
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 16px;
}

/* 热门选题 */
.hot-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hot-tag {
  display: inline-block;
  padding: 8px 12px;
  background: var(--color-background-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 12px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--color-primary);
    color: var(--color-primary);
    background: rgba(34, 197, 94, 0.05);
    transform: translateY(-1px);
  }
}

/* 创作技巧 */
.tips-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tip-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: var(--color-background-secondary);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);

  &:hover {
    background: rgba(34, 197, 94, 0.05);
  }
}

.tip-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--gradient-primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.tip-content {
  flex: 1;
  min-width: 0;
}

.tip-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 2px;
}

.tip-desc {
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.4;
}

/* 创作进度信息 */
.progress-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.progress-step {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: var(--color-background-secondary);
  border-radius: var(--radius-md);
}

.step-label {
  font-size: 12px;
  color: var(--color-text-muted);
}

.step-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
}

.progress-tip {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px;
  background: rgba(34, 197, 94, 0.08);
  border-radius: var(--radius-md);
  font-size: 12px;
  color: var(--color-primary-dark);
  line-height: 1.5;

  .anticon {
    flex-shrink: 0;
    margin-top: 2px;
  }

  &.waiting {
    background: rgba(250, 173, 20, 0.08);
    color: #d48806;
  }
}

/* 主内容区的 AI 过程时间线 */
.central-process-panel {
  width: 100%;
  max-width: 1040px;
  margin: 0 auto 24px;
  padding: 20px;
  background: #10201b;
  border: 1px solid rgba(99, 197, 145, 0.2);
  border-radius: 18px;
  box-shadow: 0 18px 42px rgba(15, 56, 38, 0.14);

  .process-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;

    .process-heading-main {
      display: flex;
      align-items: center;
      gap: 9px;
      min-width: 0;
    }

    .process-live-dot {
      width: 8px;
      height: 8px;
      flex-shrink: 0;
      border-radius: 50%;
      background: #72e2a5;
      box-shadow: 0 0 0 5px rgba(114, 226, 165, 0.12);
      animation: pulse 1.5s infinite;
    }

    .panel-title {
      margin: 0;
      color: #effbf4;

      .anticon {
        color: #72e2a5;
      }
    }

    .process-live-label {
      padding: 3px 7px;
      border: 1px solid rgba(114, 226, 165, 0.3);
      border-radius: var(--radius-full);
      color: #8fe5b6;
      font-size: 10px;
      letter-spacing: 0.08em;
    }
  }

  .process-toggle {
    flex-shrink: 0;
    border: 1px solid rgba(175, 231, 199, 0.25);
    padding: 6px 10px;
    background: transparent;
    border-radius: 8px;
    color: #bcebd0;
    font-size: 12px;
    cursor: pointer;
    white-space: nowrap;
    transition: all var(--transition-fast);

    &:hover {
      border-color: rgba(175, 231, 199, 0.5);
      background: rgba(114, 226, 165, 0.1);
      color: white;
    }
  }

  .tool-call-banner {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 16px;
    padding: 12px 14px;
    border: 1px solid rgba(114, 226, 165, 0.28);
    border-radius: 12px;
    background: rgba(114, 226, 165, 0.1);
    color: #dff8e9;

    > .anticon {
      flex-shrink: 0;
      color: #72e2a5;
      font-size: 16px;
    }

    .tool-call-copy {
      display: grid;
      gap: 2px;
      min-width: 0;
      flex: 1;

      strong {
        font-size: 13px;
        font-weight: 600;
      }

      span {
        overflow: hidden;
        color: #a9d9bc;
        font-size: 12px;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    .tool-call-state {
      color: #8fe5b6;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.08em;
    }
  }

  .process-summary {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin-top: 12px;
    padding: 10px 12px;
    border: 1px solid rgba(175, 231, 199, 0.12);
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.04);
    color: #b8d8c4;
    font-size: 13px;
    line-height: 1.5;

    .anticon {
      flex-shrink: 0;
      margin-top: 2px;
    }

    &.completed {
      color: #b8d8c4;
    }

    &.failed {
      border-color: rgba(252, 165, 165, 0.2);
      background: rgba(239, 68, 68, 0.12);
      color: #fecaca;
    }
  }

  .process-spinner {
    animation: spin 1s linear infinite;
  }

  .expand-enter-active,
  .expand-leave-active {
    transition: opacity 0.18s ease, max-height 0.18s ease;
    overflow: hidden;
  }

  .expand-enter-from,
  .expand-leave-to {
    max-height: 0;
    opacity: 0;
  }

  .expand-enter-to,
  .expand-leave-from {
    max-height: 420px;
    opacity: 1;
  }

  .logs-container {
    max-height: 460px;
    margin-top: 14px;
    overflow-y: auto;
    background: rgba(2, 12, 9, 0.34);
    border: 1px solid rgba(175, 231, 199, 0.12);
    border-radius: 12px;
    padding: 10px;

    .log-entry {
      display: flex;
      position: relative;
      gap: 8px;
      align-items: flex-start;
      padding: 8px 10px;
      font-size: 12px;
      line-height: 1.55;
      border-radius: 9px;
      margin-bottom: 5px;
      transition: background var(--transition-fast), border-color var(--transition-fast);

      &:hover {
        background: rgba(255, 255, 255, 0.05);
      }

      &.success {
        .log-time {
          color: #72e2a5;
        }
      }

      &.error {
        background: rgba(239, 68, 68, 0.1);

        .log-time {
          color: #fca5a5;
        }

        .log-message {
          color: #fecaca;
        }
      }

      &.tool {
        border: 1px solid rgba(114, 226, 165, 0.18);
        background: rgba(114, 226, 165, 0.08);
      }

      &.reasoning {
        display: block;
        padding: 10px 12px 12px 14px;
        border-left: 2px solid #72e2a5;
        background: rgba(255, 255, 255, 0.035);

        .log-message {
          color: #d8ede0;
        }
      }

      .log-time {
        flex-shrink: 0;
        padding-top: 1px;
        color: #78998a;
        font-size: 10px;
        font-weight: 500;
      }

      .log-message {
        flex: 1;
        color: #b6d0c0;
        white-space: pre-wrap;
        word-break: break-word;
      }

      .reasoning-label {
        display: flex;
        align-items: center;
        gap: 7px;
        margin-bottom: 5px;
        color: #82dba9;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      .reasoning-mark {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #72e2a5;
        box-shadow: 0 0 0 3px rgba(114, 226, 165, 0.12);
      }

      .log-tool-icon {
        display: inline-flex;
        flex-shrink: 0;
        align-items: center;
        justify-content: center;
        width: 18px;
        height: 18px;
        color: #72e2a5;
      }

      .log-tool-copy {
        display: grid;
        gap: 2px;
        min-width: 0;

        strong {
          color: #dff8e9;
          font-size: 12px;
          font-weight: 600;
        }
      }

      &.meme-result {
        align-items: flex-start;
        border: 1px solid rgba(114, 226, 165, 0.14);
        background: rgba(114, 226, 165, 0.045);
      }

      .meme-result-copy {
        display: grid;
        flex: 1;
        gap: 8px;
        min-width: 0;

        strong {
          color: #dff8e9;
          font-size: 12px;
          font-weight: 600;
        }
      }

      .meme-candidate-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 8px;
      }

      .meme-candidate {
        position: relative;
        min-width: 0;
        overflow: hidden;
        border: 1px solid rgba(175, 231, 199, 0.18);
        border-radius: 8px;
        background: rgba(2, 12, 9, 0.45);

        img {
          display: block;
          width: 100%;
          aspect-ratio: 1;
          object-fit: cover;
        }
      }

      .meme-candidate-id {
        position: absolute;
        z-index: 1;
        top: 5px;
        left: 5px;
        padding: 2px 5px;
        border-radius: 5px;
        background: rgba(2, 12, 9, 0.78);
        color: #dff8e9;
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 10px;
      }
    }

    &::-webkit-scrollbar {
      width: 6px;
    }

    &::-webkit-scrollbar-thumb {
      background: rgba(175, 231, 199, 0.28);
      border-radius: var(--radius-full);
    }

    &::-webkit-scrollbar-track {
      background: transparent;
    }
  }
}

/* 选题展示 */
.topic-display {
  padding: 12px 16px;
  background: var(--color-background-secondary);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-primary);

  p {
    margin: 0;
    font-size: 13px;
    color: var(--color-text);
    line-height: 1.6;
  }
}

/* 提示面板样式 */
.tips-section {
  .tip-icon {
    background: transparent;
    font-size: 16px;
  }

  .tip-desc {
    font-size: 12px;
  }
}

/* 文章统计 */
.stats-section {
  margin-top: auto;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.stat-item {
  text-align: center;
  padding: 16px 12px;
  background: var(--color-background-secondary);
  border-radius: var(--radius-md);
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-primary);
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: var(--color-text-muted);
}

/* 底部帮助链接 */
.panel-footer {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid var(--color-border-light);
  display: flex;
  justify-content: center;
  gap: 20px;
}

.help-link {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: color var(--transition-fast);

  &:hover {
    color: var(--color-primary);
  }
}

.action-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.action-btn {
  height: 40px;
  font-size: 13px;
  font-weight: 500;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;

  &.primary {
    background: var(--gradient-primary);
    border: none;
    color: white;

    &:hover {
      opacity: 0.9;
    }
  }
}

/* 阶段切换过渡动画 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(30px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}

/* 动画 */
@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 加载阶段样式 */
.loading-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120px 40px;
  text-align: center;

  h3 {
    font-size: 20px;
    font-weight: 600;
    color: var(--color-text);
    margin: 24px 0 8px;
  }

  p {
    font-size: 14px;
    color: var(--color-text-secondary);
    margin: 0;
  }
}

/* 大纲生成中状态 */
.outline-generating-state {
  max-width: 100%;
}

.outline-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px 20px;
  font-size: 14px;
  color: var(--color-text-secondary);
}

/* 渐入动画 */
@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.fade-in {
  animation: fade-in 0.4s ease-out;
}

/* 响应式 */
@media (max-width: 1400px) {
  .create-layout {
    grid-template-columns: 280px 1fr 260px;
  }
}

@media (max-width: 1200px) {
  .create-layout {
    grid-template-columns: 240px 1fr 220px;
  }
}

@media (max-width: 992px) {
  .article-create-page {
    height: auto;
    min-height: calc(100vh - 64px);
    overflow: visible;
  }

  .create-layout {
    grid-template-columns: 1fr;
    height: auto;
  }

  .sidebar-left,
  .sidebar-right {
    display: none;
  }

  .main-content {
    padding: 20px;
  }
}

@media (max-width: 560px) {
  .context-select-grid {
    grid-template-columns: 1fr;
  }
}
</style>
