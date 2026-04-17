<template>
  <section class="view">
    <div class="hero-card">
      <div>
        <div class="eyebrow">教学基础数据</div>
        <h2 class="hero-card__title">先选对课程和班级，再进入后续阅卷配置</h2>
        <p class="hero-card__text">
          这里参考教学平台的课程列表思路，把学年、学期、课程状态和角色放在前面筛清楚，再决定哪些班级进入本系统的阅卷链路。
        </p>
      </div>
      <div class="hero-card__meta">
        <span class="pill pill--good">数据来源：学在重邮</span>
        <span class="pill pill--warn">同步后本地缓存</span>
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
          <article v-for="item in classSyncStats" :key="item.label" class="stat-card" :class="`stat-card--${item.tone}`">
            <div class="stat-card__label">{{ item.label }}</div>
            <div class="stat-card__value">{{ item.value }}</div>
          </article>
        </div>

        <section class="panel">
          <div class="panel__header panel__header--stack">
            <div>
              <h3>班级筛选</h3>
              <p class="panel__description">先缩小教师当前负责的课程范围，再决定哪些班级启用阅卷配置。</p>
            </div>
            <div class="filter-toolbar">
              <div v-for="item in classFilters" :key="item.label" class="select-mock">
                <span class="select-mock__label">{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
              <div class="toolbar__search">搜索课程名称 / 课程代码</div>
              <button class="action-button action-button--ghost">增量同步</button>
              <button class="action-button">全量刷新</button>
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="panel__header">
            <div>
              <h3>班级工作区</h3>
              <p class="panel__description">每张卡片先展示课程上下文，再暴露“查看、绑定任务、进入配置”等动作。</p>
            </div>
          </div>

          <div class="issue-stack">
            <article v-for="item in teachingClasses" :key="`${item.course}-${item.className}`" class="course-work-card">
              <div class="course-work-card__main">
                <div class="course-work-card__cover">课</div>
                <div>
                  <div class="course-work-card__title">{{ item.course }}</div>
                  <div class="course-work-card__meta">{{ item.className }} · {{ item.term }} · {{ item.students }} 人</div>
                  <div class="course-work-card__meta">同步状态：{{ item.syncStatus }} · 最近同步：{{ item.syncTime }}</div>
                </div>
              </div>
              <div class="course-work-card__aside">
                <span class="status-badge" :class="item.status === '启用中' ? 'status-badge--good' : 'status-badge--warn'">{{ item.status }}</span>
                <div class="tag-row tag-row--end">
                  <span class="tag tag--good">查看</span>
                  <span class="tag">绑定任务</span>
                  <span class="tag">进入配置</span>
                </div>
              </div>
            </article>
          </div>
        </section>

        <section class="panel">
          <div class="panel__header">
            <h3>设计原则</h3>
          </div>
          <ul class="detail-list">
            <li v-for="item in classSyncNotes" :key="item">{{ item }}</li>
          </ul>
        </section>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
import { classFilters, classSyncNotes, classSyncStats, settingsNavGroups, teachingClasses } from "../mock-data";
</script>
