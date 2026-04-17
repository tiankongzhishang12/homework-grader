<template>
  <section class="view">
    <div class="hero-card">
      <div>
        <div class="eyebrow">任务中心</div>
        <h2 class="hero-card__title">先把任务配置做到“可开始”，再进入自动阅卷</h2>
        <p class="hero-card__text">
          当前页面把班级、任务、标准答案、评分标准、导出模板和批量路径收进同一条任务链。老师只需要判断一件事：这一项任务现在能不能直接开始阅卷。
        </p>
      </div>
      <div class="hero-card__meta">
        <span class="pill pill--good">{{ taskOverview.course }}</span>
        <span class="pill">{{ taskOverview.className }}</span>
        <span class="pill pill--warn">{{ taskOverview.taskName }}</span>
      </div>
    </div>

    <div class="task-summary-grid">
      <article class="panel task-summary-card">
        <div class="panel__header">
          <h3>当前任务</h3>
          <span class="status-badge status-badge--good">{{ taskOverview.taskType }}</span>
        </div>
        <div class="summary-grid">
          <div class="summary-item"><span>任务名称</span><strong>{{ taskOverview.taskName }}</strong></div>
          <div class="summary-item"><span>提交进度</span><strong>{{ taskOverview.submitted }}</strong></div>
          <div class="summary-item"><span>班级</span><strong>{{ taskOverview.className }}</strong></div>
          <div class="summary-item"><span>任务就绪度</span><strong>{{ taskOverview.readiness }}</strong></div>
        </div>
      </article>

      <article class="panel task-summary-card">
        <div class="panel__header">
          <h3>推荐动作</h3>
        </div>
        <div class="task-action-stack">
          <RouterLink to="/rubrics" class="action-button action-button--ghost">检查评分标准配置</RouterLink>
          <RouterLink to="/rubrics/generate" class="action-button action-button--ghost">文本生成 Rubric</RouterLink>
          <RouterLink to="/grading" class="action-button">进入批量阅卷</RouterLink>
        </div>
      </article>
    </div>

    <div class="stats-grid">
      <article v-for="item in taskStats" :key="item.label" class="stat-card" :class="`stat-card--${item.tone}`">
        <div class="stat-card__label">{{ item.label }}</div>
        <div class="stat-card__value">{{ item.value }}</div>
      </article>
    </div>

    <section class="panel">
      <div class="panel__header">
        <div>
          <h3>任务配置模块</h3>
          <p class="panel__description">每个模块只显示“是否就绪、版本、来源与动作入口”，降低老师判断成本。</p>
        </div>
      </div>

      <div class="module-grid">
        <article v-for="item in taskModules" :key="item.title" class="module-card">
          <div class="module-card__top">
            <div>
              <div class="rubric-card__title">{{ item.title }}</div>
              <div class="rubric-card__meta">{{ item.owner }} · {{ item.version }}</div>
            </div>
            <span class="status-badge" :class="item.status === '已确认' ? 'status-badge--good' : 'status-badge--warn'">{{ item.status }}</span>
          </div>
          <p class="rubric-card__summary">{{ item.summary }}</p>
          <div class="tag-row">
            <span v-for="action in item.actions" :key="action" class="tag" :class="action.includes('Rubric') ? 'tag--good' : ''">{{ action }}</span>
          </div>
        </article>
      </div>
    </section>

    <section class="panel">
      <div class="panel__header">
        <h3>开始阅卷前提示</h3>
      </div>
      <ul class="detail-list">
        <li v-for="item in taskChecklist" :key="item">{{ item }}</li>
      </ul>
    </section>
  </section>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
import { taskChecklist, taskModules, taskOverview, taskStats } from "../mock-data";
</script>
