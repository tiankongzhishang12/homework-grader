<template>
  <section class="view">
    <div class="hero-card">
      <div>
        <div class="eyebrow">阅卷结果工作区</div>
        <h2 class="hero-card__title">列表页不只是筛风险，也要承担批量查看和导出的工作区角色</h2>
        <p class="hero-card__text">
          这一页参考成绩管理页的工作区结构：顶部先筛班级和结果状态，中间保留工具条，主体区域使用可横向展开的数据表承载批量结果。
        </p>
      </div>
      <div class="hero-card__meta">
        <span class="pill pill--good">当前任务：实验三 · 需求规格说明书</span>
        <span class="pill pill--warn">结果版本：Excel 模板 v1.0</span>
      </div>
    </div>

    <div class="stats-grid">
      <article v-for="item in resultWorkbenchStats" :key="item.label" class="stat-card" :class="`stat-card--${item.tone}`">
        <div class="stat-card__label">{{ item.label }}</div>
        <div class="stat-card__value">{{ item.value }}</div>
      </article>
    </div>

    <div class="panel">
      <div class="panel__header panel__header--stack">
        <div>
          <h2>结果筛选</h2>
          <p class="panel__description">先确定班级和结果范围，再看具体学生得分、复核状态和风险标签。</p>
        </div>
        <div class="filter-toolbar">
          <div v-for="item in studentFilters" :key="item.label" class="select-mock">
            <span class="select-mock__label">{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
          <div class="toolbar__search">搜索学生 / 学号 / 匿名 ID</div>
        </div>
      </div>

      <div class="toolbar toolbar--workbench">
        <div class="tag-row">
          <span class="filter-chip filter-chip--active">全部</span>
          <span class="filter-chip">待复核</span>
          <span class="filter-chip">低置信度</span>
          <span class="filter-chip">未覆盖需求</span>
          <span class="filter-chip">一致性问题</span>
        </div>
        <div class="toolbar__actions">
          <button class="action-button action-button--ghost">显示/隐藏列</button>
          <button class="action-button action-button--ghost">导出 Excel</button>
          <button class="action-button">刷新结果</button>
        </div>
      </div>

      <div class="table-shell">
        <table class="table">
          <thead>
            <tr>
              <th>学号</th>
              <th>姓名</th>
              <th>匿名 ID</th>
              <th>原始总分</th>
              <th>百分制</th>
              <th>等级</th>
              <th>置信度</th>
              <th>门禁状态</th>
              <th>未覆盖需求</th>
              <th>一致性问题</th>
              <th>风险标签</th>
              <th>最终成绩</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="student in studentList" :key="student.id">
              <td>{{ student.studentNumber }}</td>
              <td>{{ student.name }}</td>
              <td>{{ student.id }}</td>
              <td>{{ student.rawTotalScore }}</td>
              <td>{{ student.percentileScore }}</td>
              <td>
                <span class="status-badge" :class="student.grade === '通过' ? 'status-badge--good' : 'status-badge--warn'">{{ student.grade }}</span>
              </td>
              <td>{{ student.confidence }}</td>
              <td>
                <span class="status-badge" :class="student.gateStatus === '通过' ? 'status-badge--good' : 'status-badge--risk'">{{ student.gateStatus }}</span>
              </td>
              <td>{{ student.uncoveredRequirementCount }}</td>
              <td>{{ student.consistencyIssueCount }}</td>
              <td>
                <div class="tag-row">
                  <span v-for="tag in student.riskTags" :key="tag" class="tag" :class="tag.includes('问题') || tag.includes('未覆盖') ? 'tag--warn' : 'tag--good'">{{ tag }}</span>
                </div>
              </td>
              <td><strong>{{ student.percentileScore }}</strong></td>
              <td>
                <RouterLink :to="`/students/${student.id}`" class="text-link">查看详情</RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
import { resultWorkbenchStats, studentFilters, studentList } from "../mock-data";
</script>
