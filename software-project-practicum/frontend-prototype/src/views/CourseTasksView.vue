<template>
  <section class="view">
    <div class="hero-card">
      <div>
        <div class="eyebrow">课程任务设置</div>
        <h2 class="hero-card__title">把任务列表做成真正的工作区，而不是零散配置入口</h2>
        <p class="hero-card__text">
          这一页吸收课程平台“先筛选、再进入课程”的方式，并加入任务状态分栏，让教师更容易看清哪些任务待配置、待发布、评分中。
        </p>
      </div>
      <div class="hero-card__meta">
        <span class="pill pill--good">统一抽象：作业 / 考试</span>
        <span class="pill">从任务进入规则配置</span>
      </div>
    </div>

    <div class="settings-shell">
      <aside class="settings-nav panel">
        <h3>配置中心</h3>
        <div v-for="group in settingsNavGroups" :key="group.label" class="settings-group">
          <div class="settings-group__label">{{ group.label }}</div>
          <RouterLink v-for="item in group.items" :key="item.to" :to="item.to" class="section-nav__item">
            {{ item.label }}
          </RouterLink>
        </div>
      </aside>

      <div class="detail-content">
        <div class="stats-grid">
          <article v-for="item in taskSummary" :key="item.label" class="stat-card" :class="`stat-card--${item.tone}`">
            <div class="stat-card__label">{{ item.label }}</div>
            <div class="stat-card__value">{{ item.value }}</div>
          </article>
        </div>

        <section class="panel">
          <div class="panel__header panel__header--stack">
            <div>
              <h3>任务筛选</h3>
              <p class="panel__description">按学年、学期、任务类型和配置状态筛选，先聚焦当前要处理的课程任务。</p>
            </div>
            <div class="filter-toolbar">
              <div v-for="item in taskFilters" :key="item.label" class="select-mock">
                <span class="select-mock__label">{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
              <div class="toolbar__search">搜索任务名称 / 课程名 / 课程代码</div>
              <button class="action-button">同步任务</button>
            </div>
          </div>
        </section>

        <section class="task-board">
          <article v-for="column in taskColumns" :key="column.label" class="panel task-column">
            <div class="panel__header panel__header--stack">
              <div>
                <h3>{{ column.label }}</h3>
                <p class="panel__description">{{ column.note }}</p>
              </div>
              <span class="pill">{{ column.value }}</span>
            </div>

            <div class="issue-stack">
              <article v-for="item in courseTasks.filter((task) => matchColumn(task.configStatus, column.label))" :key="item.id" class="rubric-card">
                <div class="rubric-card__top">
                  <div>
                    <div class="rubric-card__title">{{ item.name }}</div>
                    <div class="rubric-card__meta">{{ item.className }} · {{ item.type }} · 满分 {{ item.totalScore }}</div>
                  </div>
                  <span class="status-badge" :class="item.configStatus === '评分中' ? 'status-badge--warn' : 'status-badge--good'">{{ item.configStatus }}</span>
                </div>
                <p class="rubric-card__summary">截止时间：{{ item.deadline }}。当前进度：{{ item.progress }}。</p>
                <div class="tag-row">
                  <RouterLink :to="`/assignments/${item.id}`" class="tag tag--good">作业详情</RouterLink>
                  <span class="tag">查看提交</span>
                  <RouterLink :to="`/assignments/${item.id}/grading`" class="tag">批量阅卷</RouterLink>
                </div>
              </article>
            </div>
          </article>
        </section>

        <section class="panel">
          <div class="panel__header">
            <h3>推荐流程</h3>
          </div>
          <ul class="detail-list">
            <li v-for="item in taskFlow" :key="item">{{ item }}</li>
          </ul>
        </section>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
import { courseTasks, settingsNavGroups, taskColumns, taskFilters, taskFlow, taskSummary } from "../mock-data";

const matchColumn = (status: string, label: string) => {
  if (label === "待配置") return status === "待配置";
  if (label === "待发布") return status === "已发布";
  if (label === "评分中") return status === "评分中";
  return false;
};
</script>
