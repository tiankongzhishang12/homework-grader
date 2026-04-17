<template>
  <div class="toast-stack">
    <div v-for="item in uiStore.toasts" :key="item.id" class="toast" :class="`toast--${item.tone}`">
      {{ item.message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { useUiStore } from "../stores/ui";

const uiStore = useUiStore();
</script>
