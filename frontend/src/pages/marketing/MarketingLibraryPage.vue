<template>
  <div class="library-page">
    <div class="page-heading">
      <div>
        <span class="eyebrow">MARKETING LIBRARY</span>
        <h1>营销资料库</h1>
        <p>沉淀产品知识与平台规则，让每次创作都有可靠上下文。</p>
      </div>
      <a-button @click="loadData" :loading="loading">
        <template #icon><ReloadOutlined /></template>
        刷新
      </a-button>
    </div>

    <div class="library-tabs">
      <button :class="{ active: activeTab === 'products' }" @click="activeTab = 'products'">
        <DatabaseOutlined /> 产品档案 <span>{{ products.length }}</span>
      </button>
      <button :class="{ active: activeTab === 'platforms' }" @click="activeTab = 'platforms'">
        <AppstoreOutlined /> 平台规则 <span>{{ platforms.length }}</span>
      </button>
    </div>

    <a-spin :spinning="loading">
      <section v-if="activeTab === 'products'" class="panel">
        <div class="panel-heading">
          <div>
            <h2>产品档案</h2>
            <p>上传 DOCX、Markdown 或 PPT/PPTX，AI 会整理成标准档案；旧版 PPT 需要服务器安装 LibreOffice。</p>
          </div>
          <a-button type="primary" :loading="uploading" @click="openFilePicker">
            <template #icon><CloudUploadOutlined /></template>
            上传产品资料
          </a-button>
          <input
            ref="fileInput"
            class="file-input"
            type="file"
            accept=".docx,.md,.ppt,.pptx"
            @change="handleFileChange"
          />
        </div>

        <div v-if="products.length" class="product-grid">
          <article v-for="product in products" :key="product.id" class="product-card">
            <div class="card-topline">
              <div class="product-mark"><InboxOutlined /></div>
              <a-popconfirm title="确定删除这个产品档案吗？" @confirm="removeProduct(product.id)">
                <a-button type="text" danger aria-label="删除产品档案"><DeleteOutlined /></a-button>
              </a-popconfirm>
            </div>
            <div class="product-category">{{ product.profile.category || '产品档案' }}</div>
            <h3>{{ product.profile.name || product.name }}</h3>
            <p class="product-description">{{ product.profile.description || '暂无产品简介' }}</p>
            <div class="product-meta">
              <span><FileTextOutlined /> {{ product.sourceFilename }}</span>
              <span>{{ formatDate(product.createTime) }}</span>
            </div>
            <div v-if="product.profile.sellingPoints.length" class="selling-points">
              <span v-for="point in product.profile.sellingPoints.slice(0, 3)" :key="point">{{ point }}</span>
            </div>
            <a-collapse ghost>
              <a-collapse-panel key="details" header="查看完整档案">
                <div class="profile-detail">
                  <p><strong>目标受众</strong>{{ product.profile.targetAudience || '未识别' }}</p>
                  <p><strong>品牌语气</strong>{{ product.profile.brandTone || '未识别' }}</p>
                  <p><strong>核心特性</strong>{{ product.profile.coreFeatures.join('、') || '未识别' }}</p>
                  <p><strong>避免表述</strong>{{ product.profile.claimsToAvoid.join('、') || '未识别' }}</p>
                  <div v-if="product.profile.faq.length" class="faq-list">
                    <div v-for="item in product.profile.faq" :key="item.question">
                      <strong>{{ item.question }}</strong><span>{{ item.answer }}</span>
                    </div>
                  </div>
                </div>
              </a-collapse-panel>
            </a-collapse>
          </article>
        </div>
        <a-empty v-else description="还没有产品档案。上传 DOCX、Markdown 或 PPT/PPTX 开始整理。" />
      </section>

      <section v-else class="platform-grid">
        <article v-for="platform in platforms" :key="platform.id" class="platform-card">
          <div class="platform-title-row">
            <div>
              <div class="platform-key">{{ platform.platformKey }}</div>
              <h2>{{ platform.name }}</h2>
            </div>
            <a-button v-if="isAdmin" @click="editPlatform(platform)">
              <template #icon><EditOutlined /></template>
              编辑规则
            </a-button>
          </div>
          <div class="platform-section">
            <h3><TeamOutlined /> 受众特点</h3>
            <p>{{ platform.audienceDescription }}</p>
          </div>
          <div class="platform-section">
            <h3><SafetyCertificateOutlined /> 内容规则</h3>
            <p>{{ platform.contentRules }}</p>
          </div>
          <div class="format-row">
            <span>推荐形式</span>
            <strong>{{ platform.preferredFormats }}</strong>
          </div>
        </article>
        <a-empty v-if="platforms.length === 0" description="暂无平台规则" />
      </section>
    </a-spin>

    <a-modal
      v-model:open="editOpen"
      title="编辑平台资料"
      :confirm-loading="savingPlatform"
      ok-text="保存"
      cancel-text="取消"
      @ok="savePlatform"
    >
      <a-form layout="vertical">
        <a-form-item label="平台名称"><a-input v-model:value="platformForm.name" /></a-form-item>
        <a-form-item label="受众特点">
          <a-textarea v-model:value="platformForm.audienceDescription" :rows="3" />
        </a-form-item>
        <a-form-item label="内容规则">
          <a-textarea v-model:value="platformForm.contentRules" :rows="4" />
        </a-form-item>
        <a-form-item label="推荐内容形式">
          <a-textarea v-model:value="platformForm.preferredFormats" :rows="2" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  AppstoreOutlined,
  CloudUploadOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  EditOutlined,
  FileTextOutlined,
  InboxOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
} from '@ant-design/icons-vue'
import { useLoginUserStore } from '@/stores/loginUser'
import {
  deleteProductProfile,
  getMarketingPlatforms,
  getProductProfiles,
  importProductProfile,
  updateMarketingPlatform,
  type MarketingPlatform,
  type ProductProfile,
} from '@/api/marketingController'

const loginUserStore = useLoginUserStore()
const activeTab = ref<'products' | 'platforms'>('products')
const products = ref<ProductProfile[]>([])
const platforms = ref<MarketingPlatform[]>([])
const loading = ref(false)
const uploading = ref(false)
const savingPlatform = ref(false)
const fileInput = ref<HTMLInputElement>()
const editOpen = ref(false)
const selectedPlatformId = ref<number | null>(null)
const platformForm = reactive({
  name: '',
  audienceDescription: '',
  contentRules: '',
  preferredFormats: '',
})
const isAdmin = computed(() => loginUserStore.loginUser.userRole === 'admin')

const readResult = <T,>(response: { data: { code: number; data: T; message: string } }) => {
  if (response.data.code !== 0) throw new Error(response.data.message)
  return response.data.data
}

const loadData = async () => {
  loading.value = true
  try {
    const [productResponse, platformResponse] = await Promise.all([
      getProductProfiles(),
      getMarketingPlatforms(),
    ])
    products.value = readResult(productResponse) || []
    platforms.value = readResult(platformResponse) || []
  } catch (error) {
    message.error((error as Error).message || '资料加载失败')
  } finally {
    loading.value = false
  }
}

const openFilePicker = () => fileInput.value?.click()

const handleFileChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploading.value = true
  try {
    const product = readResult(await importProductProfile(file))
    products.value = [product, ...products.value]
    message.success(`已整理并保存「${product.name}」产品档案`)
  } catch (error) {
    message.error((error as Error).message || '产品档案整理失败')
  } finally {
    uploading.value = false
    input.value = ''
  }
}

const removeProduct = async (id: number) => {
  try {
    const removed = readResult(await deleteProductProfile(id))
    if (removed) products.value = products.value.filter((product) => product.id !== id)
    message.success('产品档案已删除')
  } catch (error) {
    message.error((error as Error).message || '删除失败')
  }
}

const editPlatform = (platform: MarketingPlatform) => {
  selectedPlatformId.value = platform.id
  Object.assign(platformForm, {
    name: platform.name,
    audienceDescription: platform.audienceDescription,
    contentRules: platform.contentRules,
    preferredFormats: platform.preferredFormats,
  })
  editOpen.value = true
}

const savePlatform = async () => {
  if (!selectedPlatformId.value) return
  savingPlatform.value = true
  try {
    const updated = readResult(await updateMarketingPlatform(selectedPlatformId.value, platformForm))
    platforms.value = platforms.value.map((platform) => platform.id === updated.id ? updated : platform)
    editOpen.value = false
    message.success('平台资料已更新，后续创作将自动使用新规则')
  } catch (error) {
    message.error((error as Error).message || '保存失败')
  } finally {
    savingPlatform.value = false
  }
}

const formatDate = (value: string) => new Date(value).toLocaleDateString('zh-CN')

onMounted(loadData)
</script>

<style scoped>
.library-page { max-width: 1180px; margin: 0 auto; padding: 42px 24px 72px; color: #17231f; }
.page-heading, .panel-heading, .platform-title-row { display: flex; align-items: center; justify-content: space-between; gap: 20px; }
.page-heading { margin-bottom: 30px; }
.eyebrow, .platform-key { color: #678077; font-size: 11px; font-weight: 700; letter-spacing: .12em; }
.page-heading h1 { margin: 7px 0; font-size: 30px; letter-spacing: -.04em; }
.page-heading p, .panel-heading p { margin: 0; color: #73817b; }
.library-tabs { display: flex; gap: 8px; margin-bottom: 18px; padding: 5px; width: fit-content; background: #eef3ef; border-radius: 12px; }
.library-tabs button { display: flex; gap: 9px; align-items: center; border: 0; padding: 10px 15px; border-radius: 9px; color: #64746d; background: transparent; cursor: pointer; font: inherit; }
.library-tabs button.active { background: white; color: #216e50; box-shadow: 0 2px 8px #183b2c12; }
.library-tabs button span { min-width: 21px; text-align: center; font-size: 12px; }
.panel, .platform-card { border: 1px solid #e2eae5; border-radius: 18px; background: #fff; box-shadow: 0 12px 35px #22372d08; }
.panel { padding: 24px; }
.panel-heading { padding-bottom: 22px; border-bottom: 1px solid #edf1ee; }
.panel-heading h2, .platform-card h2 { margin: 0 0 5px; font-size: 19px; }
.panel-heading p { font-size: 13px; }
.file-input { display: none; }
.product-grid, .platform-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; padding-top: 20px; }
.product-card { padding: 19px; border: 1px solid #e7eee9; border-radius: 15px; background: #fbfdfb; }
.card-topline { display: flex; justify-content: space-between; align-items: center; }
.product-mark { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 12px; color: #217150; background: #e6f3eb; }
.product-category { margin-top: 15px; color: #6e867a; font-size: 12px; }
.product-card h3 { margin: 4px 0 8px; font-size: 20px; }
.product-description { min-height: 42px; margin: 0; color: #66766e; font-size: 13px; line-height: 1.6; }
.product-meta { display: flex; justify-content: space-between; gap: 8px; margin: 15px 0; color: #87938d; font-size: 11px; }
.product-meta span { display: flex; align-items: center; gap: 5px; }
.selling-points { display: flex; flex-wrap: wrap; gap: 7px; margin-bottom: 6px; }
.selling-points span { padding: 5px 8px; border-radius: 20px; color: #287553; background: #eaf5ee; font-size: 11px; }
.profile-detail { display: grid; gap: 11px; color: #53655c; font-size: 13px; line-height: 1.55; }
.profile-detail p { margin: 0; }
.profile-detail p strong { display: inline-block; min-width: 72px; color: #263d32; }
.faq-list { display: grid; gap: 9px; }
.faq-list div { display: grid; gap: 3px; padding: 10px; border-radius: 10px; background: #f2f6f3; }
.platform-grid { padding-top: 0; }
.platform-card { padding: 22px; }
.platform-title-row { align-items: flex-start; margin-bottom: 22px; }
.platform-title-row h2 { margin: 4px 0 0; font-size: 21px; }
.platform-section { margin: 18px 0; }
.platform-section h3 { display: flex; align-items: center; gap: 8px; margin: 0 0 8px; color: #244b38; font-size: 13px; }
.platform-section p { margin: 0; color: #66766e; font-size: 13px; line-height: 1.75; }
.format-row { display: grid; gap: 5px; padding-top: 14px; border-top: 1px solid #edf1ee; color: #718078; font-size: 12px; }
.format-row strong { color: #287553; font-size: 13px; font-weight: 600; }
@media (max-width: 760px) { .library-page { padding: 28px 16px 52px; } .page-heading, .panel-heading { align-items: flex-start; flex-direction: column; } .product-grid, .platform-grid { grid-template-columns: 1fr; } .panel { padding: 17px; } }
</style>
