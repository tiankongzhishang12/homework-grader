# 智能阅卷系统后端

这是智能阅卷系统的 Spring Boot 后端骨架，实现了数据库设计方案中的主要 API 入口、文件上传、本地工作区存储、Python 脚本调度和评分进度查询。

## 技术栈

- Spring Boot 3
- Java 17
- Spring JDBC
- MySQL 8
- Springdoc OpenAPI

## 启动

```powershell
cd software-project-practicum/backend
mvn spring-boot:run
```

Swagger UI:

```text
http://localhost:8080/swagger-ui.html
```

## 配置

核心配置位于 `src/main/resources/application.yml`：

- `spring.datasource.*`：MySQL 连接信息。
- `grader.workspace-root`：本地评分工作区。
- `grader.python.executable`：Python 解释器。
- `grader.python.*-script`：预处理、评分、导出脚本白名单。

## 已实现接口范围

- 组织人员：组织树、教师、学生。
- 课程教学：课程、开课、教学班学生。
- 考核定义：考核、模板、题目、Rubric。
- 提交处理：上传、提交列表、提交详情、附件下载。
- 评分任务：启动评分、查询进度、评分任务、分项结果。
- 成绩管理：最终结果查询、确认、调整、发布、导出。
