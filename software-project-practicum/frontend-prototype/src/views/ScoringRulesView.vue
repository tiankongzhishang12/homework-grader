<template>
  <section class="view">
    <div class="hero-card">
      <div>
        <div class="eyebrow">主观题评分标准</div>
        <h2 class="hero-card__title">按题型、分值和评分策略配置主观题规则</h2>
        <p class="hero-card__text">
          每道主观题都需要明确题型、满分、评分方式和得分点拆分。界面重点不是展示一个大 rubric，而是把每道题的规则拆开看清楚。
        </p>
      </div>
      <div class="hero-card__meta">
        <span class="pill pill--good">支持：关键点 / 等级锚点 / 混合评分</span>
        <span class="pill">总分自动校验</span>
      </div>
    </div>

    <div class="settings-shell">
      <aside class="settings-nav panel">
        <h3>配置中心</h3>
        <RouterLink v-for="item in settingsNav" :key="item.to" :to="item.to" class="section-nav__item">
          {{ item.label }}
        </RouterLink>
      </aside>

      <div class="detail-content">
        <div class="stats-grid">
          <article v-for="item in scoringSummary" :key="item.label" class="stat-card" :class="`stat-card--${item.tone}`">
            <div class="stat-card__label">{{ item.label }}</div>
            <div class="stat-card__value">{{ item.value }}</div>
          </article>
        </div>

        <section class="panel">
          <div class="panel__header">
            <h3>题目评分规则</h3>
            <button class="action-button">新增主观题规则</button>
          </div>

          <div class="issue-stack">
            <article v-for="item in scoringRules" :key="item.question" class="rubric-card">
              <div class="rubric-card__top">
                <div>
                  <div class="rubric-card__title">{{ item.question }}</div>
                  <div class="rubric-card__meta">{{ item.type }} · 满分 {{ item.score }} · {{ item.strategy }}</div>
                </div>
                <span class="status-badge status-badge--good">已校验</span>
              </div>
              <ul class="detail-list">
                <li v-for="rule in item.rubric" :key="rule">{{ rule }}</li>
              </ul>
            </article>
          </div>
        </section>

        <section class="panel">
          <div class="panel__header">
            <h3>规则校验</h3>
          </div>
          <ul class="detail-list">
            <li v-for="item in scoringChecks" :key="item">{{ item }}</li>
          </ul>
        </section>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
import { scoringChecks, scoringRules, scoringSummary, settingsNav } from "../mock-data";
</script>
