<template>
  <div class="analytics-page">
    <div class="page-heading">
      <div>
        <span class="eyebrow">CAMPAIGN PERFORMANCE</span>
        <h1>营销效果</h1>
        <p>跨平台表现概览与 AI 优化建议</p>
      </div>
      <div class="heading-actions">
        <a-tag color="gold">演示数据</a-tag>
        <a-button @click="loadAnalytics" :loading="loading">
          <template #icon><ReloadOutlined /></template>刷新
        </a-button>
      </div>
    </div>

    <a-spin :spinning="loading">
      <template v-if="analytics">
        <div class="metrics-grid">
          <article v-for="metric in metrics" :key="metric.label" class="metric-card">
            <div class="metric-icon" :class="metric.tone"><component :is="metric.icon" /></div>
            <div class="metric-copy"><span>{{ metric.label }}</span><strong>{{ metric.value }}</strong></div>
            <small>{{ metric.note }}</small>
          </article>
        </div>

        <div class="main-grid">
          <section class="surface trend-surface">
            <div class="surface-heading">
              <div><span class="section-kicker">THIS MONTH</span><h2>内容表现趋势</h2></div>
              <span class="chart-legend"><i></i>曝光量</span>
            </div>
            <div ref="trendChartRef" class="trend-chart"></div>
          </section>

          <section class="surface analysis-surface">
            <div class="surface-heading">
              <div><span class="section-kicker">AI INSIGHTS</span><h2>AI 营销分析</h2></div>
              <span class="sparkle">✳</span>
            </div>
            <p class="analysis-intro">让 AI 读取同一份营销效果数据，识别平台差异并整理下一步动作。</p>
            <a-button type="primary" :loading="analyzing" @click="runAnalysis">
              <template #icon><BulbOutlined /></template>
              {{ analysis ? '重新分析' : '分析本期表现' }}
            </a-button>
            <div v-if="analysis" class="analysis-result" v-html="markdownToHtml(analysis)"></div>
            <div v-else class="analysis-placeholder">
              <BulbOutlined />
              <span>点击分析，生成基于当前 mock 数据的营销建议。</span>
            </div>
          </section>
        </div>

        <div class="lower-grid">
          <section class="surface">
            <div class="surface-heading">
              <div><span class="section-kicker">CHANNELS</span><h2>平台表现</h2></div>
              <span class="subtle">{{ analytics.period }}</span>
            </div>
            <div class="platform-list">
              <div v-for="platform in analytics.platforms" :key="platform.platform" class="platform-row">
                <div class="platform-name"><span class="platform-dot"></span><strong>{{ platform.platform }}</strong></div>
                <span>{{ formatNumber(platform.impressions) }}<small>曝光</small></span>
                <span>{{ platform.engagementRate.toFixed(1) }}%<small>互动率</small></span>
                <span>{{ platform.conversionRate.toFixed(1) }}%<small>转化率</small></span>
              </div>
            </div>
          </section>

          <section class="surface top-content-surface">
            <div class="surface-heading">
              <div><span class="section-kicker">TOP CONTENT</span><h2>高表现内容</h2></div>
              <span class="subtle">按互动量排序</span>
            </div>
            <article v-for="(item, index) in analytics.topContent" :key="item.title" class="content-row">
              <span class="content-rank">0{{ index + 1 }}</span>
              <div class="content-copy">
                <strong>{{ item.title }}</strong>
                <span>{{ item.platform }} · {{ formatNumber(item.impressions) }} 曝光</span>
              </div>
              <span class="content-conversions">{{ item.conversions }}<small>转化</small></span>
            </article>
          </section>
        </div>
      </template>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  BarChartOutlined,
  BulbOutlined,
  EyeOutlined,
  HeartOutlined,
  LinkOutlined,
  ReloadOutlined,
} from '@ant-design/icons-vue'
import * as echarts from 'echarts'
import { analyzeMarketingAnalytics, getMarketingAnalytics, type MarketingAnalytics } from '@/api/marketingController'
import { marked } from 'marked'

const analytics = ref<MarketingAnalytics | null>(null)
const loading = ref(false)
const analyzing = ref(false)
const analysis = ref('')
const trendChartRef = ref<HTMLElement>()
let trendChart: echarts.ECharts | null = null

const readResult = <T,>(response: { data: { code: number; data: T; message: string } }) => {
  if (response.data.code !== 0) throw new Error(response.data.message)
  return response.data.data
}

const metrics = computed(() => {
  const summary = analytics.value?.summary
  if (!summary) return []
  return [
    { label: '总曝光', value: formatNumber(summary.impressions), note: `${analytics.value?.period} 汇总`, icon: EyeOutlined, tone: 'green' },
    { label: '互动量', value: formatNumber(summary.engagements), note: `互动率 ${summary.engagementRate.toFixed(1)}%`, icon: HeartOutlined, tone: 'pink' },
    { label: '内容点击', value: formatNumber(summary.clicks), note: `点击率 ${summary.clickThroughRate.toFixed(1)}%`, icon: LinkOutlined, tone: 'blue' },
    { label: '转化数', value: formatNumber(summary.conversions), note: `点击转化率 ${summary.conversionRate.toFixed(1)}%`, icon: BarChartOutlined, tone: 'amber' },
  ]
})

const loadAnalytics = async () => {
  loading.value = true
  try {
    analytics.value = readResult(await getMarketingAnalytics())
    await nextTick()
    renderTrendChart()
  } catch (error) {
    message.error((error as Error).message || '营销数据加载失败')
  } finally {
    loading.value = false
  }
}

const renderTrendChart = () => {
  if (!trendChartRef.value || !analytics.value) return
  trendChart ??= echarts.init(trendChartRef.value)
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 12, right: 18, top: 18, bottom: 8, containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: analytics.value.trend.map((item) => item.date), axisLine: { lineStyle: { color: '#e6eee9' } }, axisLabel: { color: '#829087' } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#edf2ee' } }, axisLabel: { color: '#829087' } },
    series: [{
      name: '曝光量',
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 7,
      data: analytics.value.trend.map((item) => item.impressions),
      lineStyle: { width: 3, color: '#318267' },
      itemStyle: { color: '#318267', borderWidth: 2, borderColor: '#fff' },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#9bd0b5aa' }, { offset: 1, color: '#e7f3ec22' }]) },
    }],
  })
}

const runAnalysis = async () => {
  analyzing.value = true
  try {
    const result = readResult(await analyzeMarketingAnalytics())
    analysis.value = result.analysis
    if (result.toolCalls === 0) message.info('AI 已完成分析')
  } catch (error) {
    message.error((error as Error).message || 'AI 分析失败')
  } finally {
    analyzing.value = false
  }
}

const markdownToHtml = (value: string) => marked(value)
const formatNumber = (value: number) => new Intl.NumberFormat('zh-CN').format(value)
const handleResize = () => trendChart?.resize()

onMounted(() => {
  loadAnalytics()
  window.addEventListener('resize', handleResize)
})
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  trendChart = null
})
</script>

<style scoped>
.analytics-page { max-width: 1220px; margin: 0 auto; padding: 42px 24px 72px; color: #182620; }
.page-heading, .heading-actions, .surface-heading { display: flex; align-items: center; justify-content: space-between; gap: 18px; }
.page-heading { margin-bottom: 26px; }
.eyebrow, .section-kicker { color: #6d8478; font-size: 10px; font-weight: 700; letter-spacing: .13em; }
.page-heading h1 { margin: 7px 0 5px; font-size: 30px; letter-spacing: -.04em; }
.page-heading p { margin: 0; color: #79867f; }
.heading-actions { justify-content: flex-end; }
.metrics-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 16px; }
.metric-card, .surface { border: 1px solid #e4ebe6; border-radius: 17px; background: #fff; box-shadow: 0 10px 35px #23382d08; }
.metric-card { position: relative; display: flex; gap: 12px; align-items: center; min-height: 114px; padding: 19px; }
.metric-icon { display: grid; flex: 0 0 40px; place-items: center; width: 40px; height: 40px; border-radius: 13px; font-size: 17px; }
.metric-icon.green { color: #28845f; background: #e5f4eb; }.metric-icon.pink { color: #bd6784; background: #faeaf0; }.metric-icon.blue { color: #4d7eb1; background: #e9f1fa; }.metric-icon.amber { color: #a47729; background: #f8f0df; }
.metric-copy { display: grid; gap: 5px; }.metric-copy span { color: #76847c; font-size: 12px; }.metric-copy strong { font-size: 21px; letter-spacing: -.02em; }
.metric-card small { position: absolute; right: 16px; bottom: 13px; color: #9aa59f; font-size: 10px; }
.main-grid { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(300px, .9fr); gap: 16px; margin-bottom: 16px; }
.surface { padding: 22px; }.surface-heading { align-items: flex-start; }.surface-heading h2 { margin: 4px 0 0; font-size: 18px; }.subtle { color: #96a19b; font-size: 11px; }
.chart-legend { display: flex; align-items: center; gap: 7px; color: #7c8b82; font-size: 11px; }.chart-legend i { width: 7px; height: 7px; border-radius: 50%; background: #318267; }
.trend-chart { height: 270px; margin-top: 14px; }
.sparkle { color: #378667; font-size: 22px; }
.analysis-intro { margin: 17px 0; color: #7b8880; font-size: 12px; line-height: 1.7; }
.analysis-surface :deep(.ant-btn) { background: #287a59; box-shadow: none; }
.analysis-placeholder { display: flex; gap: 10px; align-items: center; margin-top: 18px; padding: 15px; border-radius: 12px; color: #849189; background: #f4f8f5; font-size: 12px; line-height: 1.5; }
.analysis-result { max-height: 290px; overflow: auto; margin-top: 17px; padding: 15px 16px; border-radius: 12px; color: #46594f; background: #f4f8f5; font-size: 12px; line-height: 1.75; }.analysis-result :deep(p) { margin: 0 0 9px; }.analysis-result :deep(p:last-child) { margin-bottom: 0; }.analysis-result :deep(h1), .analysis-result :deep(h2), .analysis-result :deep(h3) { margin: 10px 0 5px; color: #244b38; font-size: 13px; }
.lower-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }.platform-list { display: grid; gap: 4px; margin-top: 17px; }.platform-row { display: grid; grid-template-columns: minmax(120px, 1.4fr) repeat(3, minmax(62px, .7fr)); align-items: center; gap: 10px; padding: 13px 4px; border-bottom: 1px solid #eff3f0; font-size: 12px; }.platform-row:last-child { border-bottom: 0; }.platform-name { display: flex; gap: 8px; align-items: center; }.platform-dot { width: 8px; height: 8px; border-radius: 50%; background: #61a780; }.platform-row > span:not(.platform-name) { display: grid; gap: 3px; color: #34483c; font-weight: 600; }.platform-row small, .content-conversions small { color: #9aa59e; font-size: 10px; font-weight: 400; }
.top-content-surface { display: grid; align-content: start; }.content-row { display: flex; align-items: center; gap: 12px; padding: 15px 0; border-bottom: 1px solid #eff3f0; }.content-row:last-child { border-bottom: 0; }.content-rank { color: #9ab4a5; font-size: 14px; font-weight: 700; }.content-copy { display: grid; flex: 1; min-width: 0; gap: 5px; }.content-copy strong { overflow: hidden; color: #33483c; font-size: 12px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }.content-copy span { color: #99a49d; font-size: 10px; }.content-conversions { display: grid; gap: 3px; color: #328064; font-size: 13px; font-weight: 700; text-align: right; }
@media (max-width: 920px) { .metrics-grid { grid-template-columns: repeat(2, 1fr); }.main-grid, .lower-grid { grid-template-columns: 1fr; } }
@media (max-width: 580px) { .analytics-page { padding: 28px 16px 52px; }.metrics-grid { grid-template-columns: 1fr 1fr; gap: 9px; }.metric-card { min-height: 100px; padding: 13px; }.metric-icon { flex-basis: 34px; width: 34px; height: 34px; }.metric-copy strong { font-size: 17px; }.metric-card small { display: none; }.surface { padding: 17px; }.platform-row { grid-template-columns: minmax(80px, 1.1fr) repeat(3, minmax(54px, .65fr)); gap: 5px; font-size: 11px; } }
</style>
