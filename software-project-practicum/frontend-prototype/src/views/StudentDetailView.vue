<template>
  <section class="view" v-if="taskStore.currentTask && batchStore.currentStudent">
    <article class="detail-hero">
      <div>
        <div class="eyebrow">样本解释</div>
        <h2 class="detail-hero__name">{{ batchStore.currentStudent.name }} / {{ batchStore.currentStudent.studentNumber }}</h2>
        <p class="detail-hero__summary">{{ batchStore.currentStudent.summary }}</p>
      </div>
      <div class="detail-score">
        <div class="detail-score__main">{{ batchStore.currentStudent.score }}</div>
        <div class="detail-score__sub">百分制 {{ batchStore.currentStudent.percentileScore }} · 置信度 {{ batchStore.currentStudent.confidence }}</div>
        <div class="tag-row tag-row--end">
          <span class="status-badge status-badge--warn">{{ batchStore.currentStudent.grade }}</span>
        </div>
      </div>
    </article>

    <div class="toolbar__actions">
      <RouterLink :to="{ name: 'task-analysis', params: { taskId: taskStore.currentTask.id }, query: { keyword: route.query.keyword ?? '' } }" class="action-button action-button--ghost">
        返回结果列表
      </RouterLink>
    </div>

    <div class="content-grid content-grid--detail">
      <aside class="section-nav panel">
        <h3>解释结构</h3>
        <a href="#dimensions" class="section-nav__item">维度得分</a>
        <a href="#traceability" class="section-nav__item">追踪分析</a>
        <a href="#quality" class="section-nav__item">关键发现</a>
        <a href="#gates" class="section-nav__item">门禁状态</a>
      </aside>

      <div class="detail-content">
        <section id="dimensions" class="panel">
          <div class="panel__header">
            <h3>维度得分与解释</h3>
          </div>
          <div class="issue-stack">
            <article v-for="item in batchStore.currentStudent.dimensions" :key="item.id" class="dimension-editor-card">
              <div class="dimension-editor-card__top">
                <strong>{{ item.name }}</strong>
                <span class="pill">{{ item.score }}/{{ item.maxScore }} · 置信度 {{ item.confidence }}</span>
              </div>
              <p><strong>证据：</strong>{{ item.evidence }}</p>
              <p><strong>推理：</strong>{{ item.reasoning }}</p>
              <div class="content-grid content-grid--two">
                <article class="detail-list-card">
                  <h4>命中点</h4>
                  <ul>
                    <li v-for="hit in item.matched" :key="hit">{{ hit }}</li>
                  </ul>
                </article>
                <article class="detail-list-card detail-list-card--risk">
                  <h4>缺失点</h4>
                  <ul>
                    <li v-for="miss in item.missing" :key="miss">{{ miss }}</li>
                  </ul>
                </article>
              </div>
              <article class="detail-block detail-block--highlight">
                <h4>改进建议</h4>
                <p>{{ item.improvement }}</p>
              </article>
            </article>
          </div>
        </section>

        <section id="traceability" class="panel">
          <div class="panel__header">
            <h3>追踪分析</h3>
          </div>
          <div class="traceability-grid">
            <article class="trace-column">
              <h4>抽取需求</h4>
              <ul>
                <li v-for="item in batchStore.currentStudent.traceability.requirements" :key="item">{{ item }}</li>
              </ul>
            </article>
            <article class="trace-column">
              <h4>概要设计覆盖</h4>
              <div v-for="item in batchStore.currentStudent.traceability.hldCoverage" :key="item.requirement" class="trace-card">
                <div class="trace-card__top">
                  <span>{{ item.requirement }}</span>
                  <span class="trace-status" :class="`trace-status--${item.status}`">{{ item.status }}</span>
                </div>
                <p>{{ item.evidence }}</p>
              </div>
            </article>
            <article class="trace-column">
              <h4>详细设计覆盖</h4>
              <div v-for="item in batchStore.currentStudent.traceability.lldCoverage" :key="item.requirement" class="trace-card">
                <div class="trace-card__top">
                  <span>{{ item.requirement }}</span>
                  <span class="trace-status" :class="`trace-status--${item.status}`">{{ item.status }}</span>
                </div>
                <p>{{ item.evidence }}</p>
              </div>
            </article>
          </div>
          <div class="alert-strip">
            <strong>未覆盖需求：</strong>
            <span>{{ batchStore.currentStudent.traceability.uncoveredRequirements.join("、") }}</span>
          </div>
        </section>

        <section id="quality" class="panel">
          <div class="panel__header">
            <h3>关键发现</h3>
          </div>
          <ul class="detail-list">
            <li v-for="item in batchStore.currentStudent.qualityFindings" :key="item">{{ item }}</li>
          </ul>
        </section>

        <section id="gates" class="panel">
          <div class="panel__header">
            <h3>门禁与材料摘要</h3>
          </div>
          <div class="gate-grid">
            <article v-for="item in batchStore.currentStudent.gates" :key="item.name" class="gate-card">
              <div class="gate-card__top">
                <strong>{{ item.name }}</strong>
                <span class="status-badge" :class="item.passed ? 'status-badge--good' : 'status-badge--risk'">
                  {{ item.passed ? "通过" : "未通过" }}
                </span>
              </div>
              <div class="gate-card__meta">{{ item.detail }}</div>
              <div class="gate-card__meta">on_fail: {{ item.onFail }}</div>
            </article>
          </div>
          <article class="detail-list-card">
            <h4>原始材料摘要</h4>
            <ul>
              <li>文档数：{{ batchStore.currentStudent.materials.documentCount }}</li>
              <li>字数：{{ batchStore.currentStudent.materials.wordCount }}</li>
              <li>图片数：{{ batchStore.currentStudent.materials.imageCount }}</li>
              <li>角色：{{ batchStore.currentStudent.materials.roles.join("、") }}</li>
              <li v-for="log in batchStore.currentStudent.materials.logs" :key="log">{{ log }}</li>
            </ul>
          </article>
        </section>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { watch } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { useBatchStore } from "../stores/batch";
import { useTaskContextStore } from "../stores/task-context";

const route = useRoute();
const taskStore = useTaskContextStore();
const batchStore = useBatchStore();

watch(
  () => [taskStore.currentTask?.id, route.params.studentId] as const,
  async ([taskId, studentId]) => {
    if (taskId && studentId) {
      await batchStore.loadStudent(String(studentId), taskId);
    }
  },
  { immediate: true },
);
</script>
