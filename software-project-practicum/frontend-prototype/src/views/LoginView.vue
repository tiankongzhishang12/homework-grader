<template>
  <section class="auth-shell">
    <article class="auth-card">
      <div class="eyebrow">教师登录</div>
      <h1 class="auth-card__title">软件项目基础实践智能阅卷系统</h1>
      <p class="auth-card__text">当前版本面向教师端，支持任务配置、自动阅卷、结果分析和 Excel 导出。</p>

      <form class="auth-form" @submit.prevent="submit">
        <label class="field">
          <span>账号</span>
          <input v-model="username" class="field__input" type="text" autocomplete="username" placeholder="teacher" />
        </label>
        <label class="field">
          <span>密码</span>
          <input v-model="password" class="field__input" type="password" autocomplete="current-password" placeholder="123456" />
        </label>
        <p class="panel__description">演示账号：`teacher` / `123456`</p>
        <div v-if="error" class="inline-alert inline-alert--risk">{{ error }}</div>
        <button class="action-button auth-form__submit" :disabled="authStore.loading">
          {{ authStore.loading ? "登录中..." : "登录并进入任务列表" }}
        </button>
      </form>
    </article>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ApiError } from "../api/client";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();

const username = ref("teacher");
const password = ref("123456");
const error = ref("");

const submit = async () => {
  error.value = "";
  try {
    await authStore.login(username.value, password.value);
    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "/tasks";
    await router.push(redirect);
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "登录失败，请稍后重试。";
  }
};
</script>
