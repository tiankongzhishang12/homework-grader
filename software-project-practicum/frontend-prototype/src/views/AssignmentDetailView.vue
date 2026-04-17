<template>
  <section class="view">
    <div class="assignment-shell panel">
      <div class="assignment-shell__top">
        <RouterLink to="/settings/tasks" class="text-link">← 返回作业列表</RouterLink>
        <div class="assignment-shell__actions">
          <button class="action-button action-button--ghost">取消发布</button>
          <button class="action-button action-button--ghost">编辑</button>
          <RouterLink to="/assignments/exp3/grading" class="action-button">进入批量阅卷</RouterLink>
        </div>
      </div>

      <div class="assignment-heading">
        <div>
          <div class="eyebrow">{{ assignmentDetail.courseName }} · {{ assignmentDetail.courseCode }}</div>
          <h2 class="hero-card__title">{{ assignmentDetail.assignmentName }}</h2>
          <p class="hero-card__text">{{ assignmentDetail.term }} · {{ assignmentDetail.className }}</p>
        </div>
      </div>

      <div class="info-strip">
        <article v-for="item in assignmentActionCards" :key="item.title" class="info-strip__card">
          <div class="stat-card__label">{{ item.title }}</div>
          <div class="info-strip__value">{{ item.value }}</div>
          <div class="panel__subtle">{{ item.note }}</div>
        </article>
      </div>

      <div class="tab-row">
        <RouterLink v-for="item in assignmentTabs" :key="item.to" :to="item.to" class="tab-row__item" :class="item.to === '/assignments/exp3' ? 'tab-row__item--active' : ''">
          {{ item.label }}
        </RouterLink>
      </div>

      <div class="detail-content">
        <section class="panel panel--flat">
          <div class="panel__header">
            <h3>作业属性</h3>
          </div>
          <div class="summary-grid">
            <div class="summary-item"><span>活动时间</span><strong>{{ assignmentDetail.activityTime }}</strong></div>
            <div class="summary-item"><span>占成绩比例</span><strong>{{ assignmentDetail.scoreRatio }}</strong></div>
            <div class="summary-item"><span>公布成绩时间</span><strong>{{ assignmentDetail.releaseTime }}</strong></div>
            <div class="summary-item"><span>作业形式</span><strong>{{ assignmentDetail.form }}</strong></div>
            <div class="summary-item"><span>计分规则</span><strong>{{ assignmentDetail.rule }}</strong></div>
            <div class="summary-item"><span>完成指标</span><strong>{{ assignmentDetail.completion }}</strong></div>
          </div>
        </section>

        <section class="panel panel--flat">
          <div class="panel__header">
            <h3>评分方式</h3>
            <button class="action-button action-button--ghost">选择量规</button>
          </div>
          <div class="detail-blocks">
            <article class="detail-block">
              <h4>当前模式</h4>
              <p>{{ assignmentDetail.rubricMode }}</p>
            </article>
            <article class="detail-block">
              <h4>当前量规</h4>
              <p>{{ assignmentDetail.rubricName }}</p>
            </article>
          </div>
        </section>

        <section class="panel panel--flat">
          <div class="panel__header">
            <h3>作业说明</h3>
          </div>
          <article class="detail-block detail-block--highlight">
            <p>{{ assignmentDetail.description }}</p>
          </article>
        </section>

        <section class="panel panel--flat">
          <div class="panel__header">
            <h3>阅卷提醒</h3>
          </div>
          <div class="issue-stack">
            <article v-for="item in assignmentAlerts" :key="item" class="notice-card">
              {{ item }}
            </article>
          </div>
        </section>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
import { assignmentActionCards, assignmentAlerts, assignmentDetail, assignmentTabs } from "../mock-data";
</script>
