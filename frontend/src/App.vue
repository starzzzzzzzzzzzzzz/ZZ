<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const selectedKeys = ref<string[]>([route.path])

const menuItems = [
  {
    key: '/knowledge',
    label: '知识库'
  },
  {
    key: '/chat',
    label: '对话'
  }
]

const handleMenuClick = ({ key }: { key: string }) => {
  router.push(key)
}

watch(
  () => route.path,
  (path) => {
    selectedKeys.value = [path]
  }
)
</script>

<template>
  <a-layout class="app-container">
    <a-layout-header class="header">
      <div class="logo">知识库助手</div>
      <a-menu
        v-model:selectedKeys="selectedKeys"
        theme="dark"
        mode="horizontal"
        :items="menuItems"
        @click="handleMenuClick"
      />
    </a-layout-header>
    <a-layout-content>
      <router-view />
    </a-layout-content>
  </a-layout>
</template>

<style scoped>
.app-container {
  min-height: 100vh;
}

.header {
  display: flex;
  align-items: center;
  padding: 0 24px;
}

.logo {
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  margin-right: 48px;
}

:deep(.ant-layout-header) {
  background: #001529;
}

:deep(.ant-menu) {
  flex: 1;
  background: transparent;
}
</style>
