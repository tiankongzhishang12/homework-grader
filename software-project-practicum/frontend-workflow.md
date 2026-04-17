# 软件项目基础实训评分系统工作流程

## 1. 目标

本文用于明确 `software-project-practicum` 这套评分系统在引入前端页面后的整体工作流程。

当前约定的技术职责如下：

- 前端：`Vue`
- 后端：`Spring Boot`
- 评分执行层：现有 `Python` 脚本

核心原则：

- 前端不直接调用 Python
- Spring Boot 作为唯一业务后端
- Python 继续保持脚本形态，负责预处理、评分、导出

---

## 2. 整体架构

系统整体链路如下：

```text
前端页面
  -> 调用 Spring Boot 接口
Spring Boot
  -> 保存上传文件
  -> 调用 Python 脚本
  -> 读取评分结果
  -> 返回前端
Python 脚本
  -> 文本抽取
  -> 生成 IR
  -> 大模型评分
  -> 导出报表
```

更具体的处理路径如下：

```text
前端上传学生作业
  -> Spring Boot 保存到 workspace/practicum-batch/raw/
  -> Spring Boot 调用 preprocess_student_dirs.py
  -> Python 生成 ir/*.json 和 student-mapping.csv
  -> Spring Boot 调用 batch_score_reports.py
  -> Python 生成 scores/*.json 和 progress.json
  -> Spring Boot 读取评分结果
  -> 前端展示总览、列表、详情、统计
  -> 如需导出，再调用 export_traceability_excel.py
```

---

## 3. 分层职责

### 3.1 前端职责

前端负责：

- 上传学生作业文件
- 发起预处理任务
- 发起评分任务
- 查询任务进度
- 展示评分结果
- 展示统计分析
- 发起导出报表

前端不负责：

- 文本抽取
- 调用大模型
- 直接解析原始文档
- 直接调用 Python 脚本

### 3.2 Spring Boot 职责

后端负责：

- 接收上传文件
- 保存文件到工作区
- 调用 Python 脚本
- 读取 `progress.json`
- 读取 `scores/*.json`
- 聚合学生列表和详情数据
- 将结果封装为前端接口

后端是整个系统的调度中心。

### 3.3 Python 职责

Python 层负责：

- 预处理学生作业
- 抽取文本内容
- 识别文档角色
- 生成 IR 中间结果
- 基于 rubric 调用大模型评分
- 生成评分结果
- 导出 Excel 报表

Python 当前保持命令行脚本形态，不额外封装为 HTTP 服务。

---

## 4. 工作区约定

本阶段先固定使用以下目录：

`D:\grade code\homework-grader\software-project-practicum`

核心工作区：

`software-project-practicum/workspace/practicum-batch`

关键目录与文件：

- `raw/`：上传后的学生原始作业
- `ir/`：预处理后的中间结果
- `scores/`：评分结果
- `reports/`：导出报表
- `progress.json`：批次进度
- `student-mapping.csv`：匿名 ID 与学生信息映射

---

## 5. 核心处理流程

### 5.1 上传阶段

流程：

1. 教师在前端页面上传学生作业文件
2. 前端调用 Spring Boot 上传接口
3. Spring Boot 将文件保存到 `workspace/practicum-batch/raw/`

说明：

- 第一版建议支持批量上传
- 上传完成后不自动评分
- 上传和后续处理分开，便于排查问题

### 5.2 批改阶段（内部包含预处理与评分）

流程：

1. 教师点击“开始批改”
2. 前端调用后端统一批改接口
3. Spring Boot 先调用 `preprocess_student_dirs.py`
4. Python 从 `raw/` 中读取作业文件
5. Python 完成文本抽取、角色识别、IR 生成
6. 结果写入 `ir/` 和 `student-mapping.csv`
7. Spring Boot 再调用 `batch_score_reports.py`
8. Python 读取 `ir/*.json`
9. Python 调用大模型执行评分
10. Python 生成 `scores/*.json`
11. Python 更新 `progress.json`

输出结果：

- `ir/*.json`
- `scores/*.json`
- `progress.json`
- `student-mapping.csv`

这一阶段的意义：

- 确认文件是否上传完整
- 确认每个学生是否被正确识别
- 确认需求文档、概设、详设是否被抽取到
- 最终完成整批评分

批改过程内部仍然分为两个连续阶段：

- 预处理
- 评分

评分内容包括：

- 维度得分
- 证据与推理
- 改进建议
- 门禁检查结果
- traceability 分析
- 一致性问题
- 未覆盖需求

### 5.4 结果展示阶段

流程：

1. 前端定时查询进度接口，或通过 SSE 获取进度
2. 评分完成后，前端请求学生列表接口
3. 前端请求学生详情接口
4. 前端请求统计分析接口
5. 页面展示总览、列表、详情、统计

### 5.5 导出阶段

流程：

1. 教师点击“导出报表”
2. 前端调用后端导出接口
3. Spring Boot 调用 `export_traceability_excel.py`
4. Python 读取 `scores/` 和 `student-mapping.csv`
5. Python 生成 Excel 到 `reports/`
6. 后端返回下载信息给前端

输出结果：

- `reports/*.xlsx`

---

## 6. 推荐前端操作流程

建议前端页面按以下顺序引导用户操作：

1. 上传学生作业
2. 开始批改
3. 查看总览
4. 查看学生列表
5. 查看学生详情
6. 导出 Excel 报表

这样设计的好处：

- 老师视角更简单，只需理解“开始批改”
- 系统内部仍然保留预处理和评分两个阶段
- 页面仍然可以通过进度状态区分当前处于哪一步
- 后期如有需要，仍可增加高级操作入口

---

## 7. 前端按钮与后端接口建议

| 前端动作 | Spring Boot API | 后端动作 | Python脚本 |
|---|---|---|---|
| 上传学生作业 | `POST /api/batch/upload` | 保存文件到 `raw/` | 无 |
| 开始批改 | `POST /api/batch/start` | 依次执行预处理与评分 | `preprocess_student_dirs.py` + `batch_score_reports.py` |
| 查看进度 | `GET /api/batch/progress` | 读取 `progress.json` | 无 |
| 查看学生列表 | `GET /api/students` | 聚合 `scores/*.json` | 无 |
| 查看学生详情 | `GET /api/students/{id}` | 读取单个学生评分结果 | 无 |
| 查看统计 | `GET /api/analytics` | 聚合所有评分结果 | 无 |
| 导出报表 | `POST /api/batch/export` | 执行导出任务 | `export_traceability_excel.py` |

---

## 8. 为什么不直接给每个 Python 脚本做 HTTP 接口

当前阶段不建议给每个 Python 脚本额外封装 Flask 或 FastAPI 接口，原因如下：

- 现有脚本已经可以独立运行
- 直接命令行调用改动最小
- 系统复杂度更低
- 更适合当前单机工作区模式
- 先把前后端主流程跑通更重要

当前更推荐的方式是：

```text
前端 -> Spring Boot API -> ProcessBuilder 调 Python 脚本 -> 读取结果文件 -> 返回前端
```

只有在后续出现以下需求时，再考虑把 Python 独立成服务：

- 多机部署
- 分布式任务执行
- Python 服务单独扩容
- 更复杂的任务队列与监控

---

## 9. 后续设计建议

在本流程基础上，下一阶段可以继续细化：

- 前端页面功能说明
- Spring Boot 接口文档
- 前端上传页面设计
- 任务进度展示方式
- 学生详情页结构
- 统计分析页结构

当前优先级建议为：

1. 先把前端页面方案做完整
2. 再设计 Spring Boot 接口
3. 最后实现前后端联调

---

## 10. 当前结论

目前确认的系统流程为：

`前端上传 -> Spring Boot 落盘 -> Spring Boot 调 Python 预处理/评分/导出 -> Spring Boot 读结果 -> 前端展示`

这是当前 `software-project-practicum` 最适合的演进方式。
