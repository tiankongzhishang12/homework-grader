<template>
  <section class="view" v-if="taskStore.currentTask">
    <div class="hero-card">
      <div>
        <div class="eyebrow">标准答案设置</div>
        <h2 class="hero-card__title">支持导入标准答案文件，并在激活前完成解析预览</h2>
        <p class="hero-card__text">
          标准答案不是一段静态说明，而是任务配置中的正式对象。新文件上传后会先进入解析流程，只有老师手动激活后才会替换当前使用版本。
        </p>
      </div>
      <div class="hero-card__meta">
        <span class="pill pill--good">{{ taskStore.currentTask.taskName }}</span>
        <span class="pill">{{ currentVersionLabel }}</span>
      </div>
    </div>

    <div class="content-grid content-grid--two">
      <section class="panel">
        <div class="panel__header">
          <div>
            <h3>当前使用版本</h3>
            <p class="panel__description">已开始阅卷的任务不会自动切换到新版本，必须由教师手动激活。</p>
          </div>
          <button class="action-button" :disabled="configStore.saving" @click="triggerUpload">
            {{ configStore.saving ? "处理中..." : "上传标准答案文件" }}
          </button>
          <input ref="fileInput" class="hidden-input" type="file" accept=".doc,.docx,.pdf" @change="onFileChange" />
        </div>

        <div v-if="currentAnswer" class="detail-blocks">
          <article class="detail-block">
            <h4>版本信息</h4>
            <div class="form-mock">
              <div class="form-mock__row"><span>版本号</span><strong>{{ currentAnswer.version }}</strong></div>
              <div class="form-mock__row"><span>文件名</span><strong>{{ currentAnswer.fileName }}</strong></div>
              <div class="form-mock__row"><span>上传时间</span><strong>{{ currentAnswer.uploadedAt }}</strong></div>
              <div class="form-mock__row"><span>最近激活</span><strong>{{ currentAnswer.activatedAt ?? "尚未激活" }}</strong></div>
            </div>
          </article>
          <article class="detail-block">
            <h4>解析结果</h4>
            <div class="form-mock">
              <div class="form-mock__row"><span>解析状态</span><strong>{{ parseStatusLabel(currentAnswer.parseStatus) }}</strong></div>
              <div class="form-mock__row"><span>题目/条目数</span><strong>{{ currentAnswer.itemCount }}</strong></div>
              <div class="form-mock__row"><span>配置状态</span><strong>{{ configStatusLabel(currentAnswer.status) }}</strong></div>
            </div>
          </article>
        </div>
      </section>

      <section class="panel">
        <div class="panel__header">
          <h3>操作说明</h3>
        </div>
        <ul class="detail-list">
          <li>支持上传 `.doc`、`.docx`、`.pdf` 标准答案文件。</li>
          <li>新文件默认先进入草稿或解析失败状态，不会自动替换当前版本。</li>
          <li>若文件名包含 `fail`，演示环境会模拟解析失败，用于验证异常状态展示。</li>
        </ul>
      </section>
    </div>

    <section class="panel">
      <div class="panel__header">
        <h3>版本历史</h3>
        <button class="action-button action-button--ghost" :disabled="refreshing" @click="reloadAnswers">
          {{ refreshing ? "刷新中..." : "查看历史版本" }}
        </button>
      </div>

      <div class="table-shell">
        <table class="table">
          <thead>
            <tr>
              <th>版本</th>
              <th>文件名</th>
              <th>上传时间</th>
              <th>解析状态</th>
              <th>配置状态</th>
              <th>条目数</th>
              <th>当前版本</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in configStore.answers" :key="item.id">
              <td>{{ item.version }}</td>
              <td>{{ item.fileName }}</td>
              <td>{{ item.uploadedAt }}</td>
              <td>{{ parseStatusLabel(item.parseStatus) }}</td>
              <td>{{ configStatusLabel(item.status) }}</td>
              <td>{{ item.itemCount }}</td>
              <td>{{ item.current ? "是" : "否" }}</td>
              <td>
                <div class="tag-row">
                  <span class="tag">预览解析结果</span>
                  <button class="tag-button" :disabled="item.current || item.status === 'parse_failed' || configStore.saving" @click="activate(item.id)">
                    设为当前版本
                  </button>
                </div>
                <div v-if="item.status === 'parse_failed'" class="inline-alert inline-alert--risk">
                  {{ item.parseMessage ?? "解析失败，请重试。" }}
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";

const taskStore = useTaskContextStore();
const configStore = useConfigStore();
const fileInput = ref<HTMLInputElement | null>(null);
const refreshing = ref(false);

watch(
  () => taskStore.currentTask?.id,
  async (taskId) => {
    if (taskId) {
      await configStore.loadTaskConfig(taskId);
    }
  },
  { immediate: true },
);

const currentAnswer = computed(() => configStore.answers.find((item) => item.current) ?? configStore.answers[0] ?? null);
const currentVersionLabel = computed(() => (currentAnswer.value ? `当前版本：${currentAnswer.value.version}` : "当前暂无版本"));

const parseStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    uploading: "上传中",
    parsing: "解析中",
    parse_failed: "解析失败",
    draft: "解析成功（草稿）",
    confirmed: "已确认",
    in_use: "使用中",
  };
  return map[status] ?? status;
};
const configStatusLabel = (status: string) => {
  const map: Record<string, string> = { draft: "草稿", confirmed: "已确认", in_use: "使用中", parse_failed: "解析失败" };
  return map[status] ?? status;
};

const triggerUpload = () => fileInput.value?.click();

const onFileChange = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file || !taskStore.currentTask) return;
  await configStore.uploadAnswer(taskStore.currentTask.id, file);
  (event.target as HTMLInputElement).value = "";
};

const activate = async (versionId: string) => {
  if (!taskStore.currentTask) return;
  await configStore.activateAnswer(taskStore.currentTask.id, versionId);
};

const reloadAnswers = async () => {
  if (!taskStore.currentTask) return;
  refreshing.value = true;
  try {
    await configStore.loadTaskConfig(taskStore.currentTask.id);
  } finally {
    refreshing.value = false;
  }
};
</script>
