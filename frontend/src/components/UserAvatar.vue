<template>
  <a-avatar v-if="src" :src="src" :size="size" class="user-avatar" />
  <a-avatar v-else :size="size" class="user-avatar">
    <template #icon>
      <UserOutlined />
    </template>
  </a-avatar>
</template>

<script setup lang="ts">
import { UserOutlined } from '@ant-design/icons-vue'

/**
 * 用户头像：有图片地址时显示图片，否则显示默认的用户图标。
 */
withDefaults(
  defineProps<{
    src?: string | null
    size?: number
  }>(),
  {
    src: '',
    size: 36,
  },
)
</script>
