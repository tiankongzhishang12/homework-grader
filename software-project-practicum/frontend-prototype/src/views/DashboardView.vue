<template>
  <section class="view">
    <div class="hero-card">
      <div>
        <div class="eyebrow">第一版静态原型</div>
        <h2 class="hero-card__title">先做教师视角的评分评审工作台，而不是普通成绩后台</h2>
        <p class="hero-card__text">
          当前页面聚焦三件事：看整体风险、快速筛人、进入详情定位问题。上传、预处理、评分和导出入口先用静态按钮串起来，后续再接真实接口。
        </p>
      </div>
      <div class="hero-card__meta">
        <span class="pill pill--good">批次：practicum-batch</span>
        <span class="pill pill--warn">最近更新：2026-04-16 10:30</span>
      </div>
    </div>

    <div class="stats-grid">
      <article v-for="item in dashboardStats" :key="item.label" class="stat-card" :class="`stat-card--${item.tone}`">
        <div class="stat-card__label">{{ item.label }}</div>
        <div class="stat-card__value">{{ item.value }}</div>
      </article>
    </div>

    <div class="content-grid content-grid--two">
      <section class="panel">
        <div class="panel__header">
          <h3>高风险学生</h3>
          <RouterLink to="/students" class="text-link">查看全部</RouterLink>
        </div>
        <div class="risk-list">
          <article v-for="student in riskStudents" :key="student.id" class="risk-card">
            <div class="risk-card__top">
              <div>
                <div class="risk-card__name">{{ student.name }}</div>
                <div class="risk-card__meta">{{ student.studentNumber }} · {{ student.id }}</div>
              </div>
              <div class="risk-card__score">{{ student.score }}</div>
            </div>
            <p class="risk-card__summary">{{ student.summary }}</p>
            <div class="tag-row">
              <span v-for="tag in student.tags" :key="tag" class="tag tag--warn">{{ tag }}</span>
            </div>
          </article>
        </div>
      </section>

      <section class="panel">
        <div class="panel__header">
          <h3>分数分布</h3>
          <span class="panel__subtle">静态示意</span>
        </div>
        <div class="chart-card">
          <div class="chart-bar-group">
            <div class="chart-bar chart-bar--s" style="height: 24%"><span>60-69</span></div>
            <div class="chart-bar chart-bar--m" style="height: 52%"><span>70-79</span></div>
            <div class="chart-bar chart-bar--l" style="height: 78%"><span>80-89</span></div>
            <div class="chart-bar chart-bar--s" style="height: 22%"><span>90+</span></div>
          </div>
          <p class="chart-caption">当前样例批次中，成绩主要集中在 70-89 分段，低分样本多与用例规约和架构适配不足有关。</p>
        </div>
      </section>
    </div>

    <div class="content-grid content-grid--two">
      <section class="panel">
        <div class="panel__header">
          <h3>高频失分维度</h3>
        </div>
        <ul class="rank-list">
          <li class="rank-item"><span>用例图、涉众分析与用例规约质量</span><strong>12 次</strong></li>
          <li class="rank-item"><span>系统架构设计对需求的适配性</span><strong>9 次</strong></li>
          <li class="rank-item"><span>界面详细设计与需求匹配度</span><strong>6 次</strong></li>
        </ul>
      </section>

      <section class="panel">
        <div class="panel__header">
          <h3>典型问题</h3>
        </div>
        <div class="issue-stack">
          <article v-for="issue in topIssues" :key="issue.title" class="issue-card" :class="issue.level === 'risk' ? 'issue-card--risk' : 'issue-card--warn'">
            <div class="issue-card__title">{{ issue.title }}</div>
            <div class="issue-card__detail">{{ issue.detail }}</div>
          </article>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
import { dashboardStats, riskStudents, topIssues } from "../mock-data";
</script>
