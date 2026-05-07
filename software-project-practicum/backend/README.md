# 智能阅卷系统后端

这是智能阅卷系统的 Spring Boot 后端，负责组织课程数据、任务配置、学生提交、阅卷进度、评分结果、教师复核、成绩发布和导出等 API。

当前后端仍保留 Python 脚本调度能力，用于衔接已有的预处理、批量评分和导出脚本。这是现有工作流的一部分，不是特定助手平台的专属依赖。

## 技术栈

- Spring Boot 3
- Java 17
- Spring JDBC
- MySQL
- Springdoc OpenAPI

## 启动

```powershell
cd software-project-practicum/backend
mvn spring-boot:run
```

Swagger UI：

```text
http://localhost:8080/swagger-ui.html
```

## 配置

核心配置位于：

```text
src/main/resources/application.yml
```

主要配置项：

- `spring.datasource.*`：MySQL 连接信息。
- `grader.workspace-root`：本地阅卷工作区。
- `grader.python.executable`：Python 解释器路径。
- `grader.python.preprocess-script`：预处理脚本。
- `grader.python.grading-script`：批量评分脚本。
- `grader.python.export-script`：导出脚本。

如后续要把 Python 脚本替换为纯 Java 或服务化评分引擎，应先确认前端调用、数据库写入和导出流程，再分阶段迁移。

## 已实现接口范围

- 组织人员：组织树、教师、学生。
- 课程教学：课程、开课、教学班、班级学生。
- 考核定义：考核任务、模板、题目、Rubric。
- 提交处理：文件上传、提交列表、提交详情、附件下载。
- 阅卷任务：启动阅卷、进度查询、评分运行、分项结果。
- 成绩管理：最终结果查询、确认、调整、发布、导出。

## 关键模块

- `controller/`：REST API。
- `service/`：业务服务。
- `repository/`：JDBC 数据访问。
- `storage/`：本地文件存储。
- `client/python/`：Python 脚本调度客户端。
- `config/`：配置属性、拦截器和 Web 配置。
