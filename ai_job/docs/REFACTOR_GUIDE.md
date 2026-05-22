# Python 重构学习导读（面向 Java 开发者）

这次重构的目标是：**降低耦合、按职责分层、保留行为兼容**。  
你可以把它理解为把原来“多个工具类和流程类揉在一起”的代码，拆成了更清晰的 package。

## 1. 新增目录结构与职责

- `app/common/runtime_config.py`
  - 统一处理运行时配置读取（`runtime_config.json`）和环境变量解析。
  - 提供 `resolve_bool_setting/resolve_float_setting/resolve_int_setting`。
  - 统一优先级：`env > runtime_config.json > default`。

- `app/session/stage_logger.py`
  - 统一“管道阶段日志”的输出逻辑。
  - `user_session.py` 不再自己维护日志格式细节。

- `app/pipeline/payloads.py`
  - 统一生成管道步骤 payload（对抗审查、画像补充、历史记忆线性化）。
  - `role_pipeline.py` 只关心“流程控制 + 调用 LLM”，不关心字符串拼接细节。

## 2. 关键解耦点

### 2.1 user_session 的解耦

重构前：  
- 自己处理 runtime config 读取与 bool 解析；
- 自己实现 stage 日志输出。

重构后：  
- 使用 `app/common/runtime_config.py` 做配置决策；
- 使用 `app/session/stage_logger.py` 做日志输出；
- 文件更专注于“会话编排（orchestration）”。

### 2.2 pipeline_llm 的解耦

重构前：  
- 内部重复实现了配置文件读取 + env 解析 + 默认值处理。

重构后：  
- 复用 `runtime_config.py` 的通用解析器；
- 该模块只保留“LLM 调用本身”相关逻辑。

### 2.3 role_pipeline 的解耦

重构前：  
- 既负责流程，又负责大段 payload 文本构造。

重构后：  
- payload 构造移动到 `app/pipeline/payloads.py`；
- `role_pipeline.py` 聚焦于“去噪/压缩/对抗/画像建议”的步骤组合。

## 3. 推荐阅读顺序（适合 Java 背景）

1. `user_session.py`  
   先看主流程入口，理解“编排层”在做什么。
2. `role_pipeline.py`  
   再看每个 pipeline stage 的业务步骤。
3. `pipeline_llm.py`  
   看技术细节：模型选择、structured output、超时与重试。
4. `app/common/runtime_config.py`  
   看基础设施层，理解配置优先级和解析。
5. `app/pipeline/payloads.py` + `app/session/stage_logger.py`  
   看“单一职责”的辅助模块如何被复用。

## 4. 对照 Java 的理解方式

- `user_session.py` ≈ `ApplicationService` / `UseCase` 编排层
- `role_pipeline.py` ≈ 领域流程服务（组合多个步骤）
- `pipeline_llm.py` ≈ 外部网关适配层（infra adapter）
- `app/common/runtime_config.py` ≈ 配置基础设施工具类
- `app/pipeline/payloads.py` ≈ builder/helper（组装请求体）

## 5. 下一步可继续优化（可选）

- 把 `user_model.py` 按“类型定义 / 校验 / prompt 构造”再细拆为多个模块；
- 给 `app/pipeline/payloads.py` 加单元测试，锁定 payload 格式；
- 增加 `tests/` 目录，先从 `runtime_config.py` 的解析函数开始做参数化测试。
