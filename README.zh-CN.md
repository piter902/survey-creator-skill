# survey-creator-skill

[English](./README.md) | 简体中文

**一个面向 Codex、Claude、Trae、Cursor 等 AI Agent 工作流的生产级问卷 skill。**

`survey-creator-skill` 是一个开源的 **agent skill 仓库**，用来约束 AI 生成问卷 schema，并输出经过合法性校验的 HTML 问卷页面。

它的目标不只是“生成 HTML”，而是帮助 Agent：

- 校验问卷 schema 的结构与字段合法性
- 修复安全范围内可自动修复的问题
- 渲染可提交的 HTML 问卷页面
- 通过浏览器运行时 / E2E 检查空白页与关键交互
- 校验可访问性
- 校验提交 payload 协议
- 校验 payload 与具体 schema 的一一对应关系

如果你希望 AI 生成问卷时，**不是只出一个能看但不一定能交付的页面**，而是得到一套可校验、可提交、可回收数据的结果，这个项目就是为此设计的。

---

## 为什么要做这个 skill

很多 AI Agent 或“AI 表单 / AI 问卷生成器”只做到：

- 生成一份 JSON
- 渲染一份 HTML
- 假设提交数据大概率没问题

但真实业务场景里，这远远不够。

问卷系统至少要保证：

- schema 合法
- id 唯一且稳定
- 逻辑不会破坏必填校验
- 被隐藏 / 跳过的题目不会混进提交结果
- 页面不会打开白屏
- 交互可在浏览器里真实跑通
- 提交 payload 必须和当前问卷 schema 严格一致

`survey-creator-skill` 的作用，就是把这整条链路沉淀成一个可复用的 skill。

---

## 这个 skill 仓库包含什么

你可以把它理解成一个“可被 Agent 读取、检索、执行”的问卷能力包，而不是普通前端模板仓库。

### 1. Skill 层
- `SKILL.md`
- 基于自然语言理解生成问卷 schema
- schema-first 工作流
- legality-first 交付原则

### 2. Reference 层
- schema 说明
- 各题型字段说明
- 富文本规则
- 分页规则
- child 输入规则
- local cache 规则
- logic 规则与示例
- submission contract

### 3. Runtime 层
- 固定 HTML 模板
- 前端步进流转
- 显隐 / 跳题 / 跳页 / 结束逻辑
- 本地缓存处理
- payload 组装

### 4. Validation 层
- schema 校验
- schema 自动修复
- HTML runtime 校验
- HTML E2E 校验
- HTML 交互 E2E 校验
- accessibility 校验
- payload 校验
- payload-against-schema 校验
- reference consistency 校验

---

## 当前支持的题型 / 节点

- survey
- radio
- checkbox
- input
- score
- nps
- Pagination
- finish

## 当前支持的 toC 风格包

- `consumer-minimal`
- `consumer-polished`
- `consumer-trust`
- `consumer-editorial`
- `consumer-utility`
- `consumer-campaign`

---

## 当前支持的核心能力

- 欢迎页 / 结束页
- 单选 / 多选 / 输入题
- 评分题 / NPS 题
- child 输入
- 富文本 title / description
- media（image / video / audio）
- onePageOneQuestion
- allowBack
- localStorage 步进缓存
- 提交后清空缓存
- 必填校验
- 逻辑控制：
  - show_question
  - hide_question
  - show_option
  - hide_option
  - auto_select_option
  - jump_to_question
  - jump_to_page
  - end_survey
- `end_survey` 可定向跳转到指定 `finish[].id`
- 支持多结束页，用于不同用户分支的差异化结束态
- 每个 `finish[]` 都可以可选配置 `postSubmit.redirect`
- 跳转只会在“提交成功之后”执行，不会绕过问卷结果回收
- 隐藏 / 跳过题目的 required 自动豁免
- 逻辑冲突按“后触发覆盖前触发”执行

---

## 适合哪些场景

- AI 生成问卷
- 满意度调查
- 报名问卷
- 用户研究
- 产品反馈收集
- 筛选 / 分流式问卷
- NPS / 评分 / 调研场景

---

## skill 仓库结构

```text
survey-creator-skill/
├── SKILL.md                  # Agent 读取的主 skill 定义
├── README.md                 # 英文使用说明
├── README.zh-CN.md           # 中文使用说明
├── docs/                     # 给人看的辅助文档
├── references/               # 给模型读取的 schema / logic 约束
├── templates/                # HTML 模板资源
├── validators/               # 校验与渲染辅助层
├── examples/                 # 示例 schema 与 HTML
├── tests/                    # contract tests
├── evals/                    # 评估样例
└── LICENSE
```

---

## 运行依赖

这个 skill 可以开源复用，但它**不是零依赖**的。

如果别人要完整跑通「schema 校验 → HTML 渲染 → 浏览器 E2E / 交互校验 → payload 校验」这条链路，目标环境需要具备：

- Python **3.10+**
- Node.js **18+**
- npm

### 为什么同时需要 Python 和 Node

- `validators/*.py` 负责 schema 校验、渲染、payload 校验、整条 pipeline 编排
- `validators/package.json` 提供 Playwright 依赖，用于浏览器级校验

### 一次性安装

在仓库根目录执行：

```bash
cd validators
npm install
npx playwright install
```

### 构建最终单文件模板

现在仓库把可编辑模板源码放在：

- `template-src/partials/`

最终给 skill / validator 使用的单文件产物仍然输出到：

- `templates/base-survey-template.html`

构建命令：

```bash
python3 tools/build_template.py
```

### 推荐运行环境

- 推荐使用 macOS / Linux
- Windows 用户建议使用 **WSL**
- 如果没有安装 Playwright 浏览器，HTML 的 E2E / interaction 校验会失败，但 schema 校验本身仍可能正常工作

### 给开源使用者的最小预期说明

如果别人只是把这个仓库当作 Agent 的检索材料使用，只读取这些内容：

- `SKILL.md`
- `references/`
- `templates/`

那么可以先不跑完整依赖。

但如果希望这个 skill 真正执行合法性校验并输出可交付结果，就应先安装上面的依赖。

---

## 在 AI Agent / IDE 中使用

这个仓库的主定位是：**作为 skill 给 Codex、Claude、Trae、Cursor 等 Agent 使用**，而不是优先面向“手工执行脚本”的独立工具。

推荐环境：

- Codex
- Claude / Claude Code 类本地 skill 工作流
- Trae
- Cursor

---

## Codex

推荐方式：

1. 把仓库放到本地 skills 目录
   - `~/.codex/skills/survey-creator-skill`
   - 或 `~/.agents/skills/survey-creator-skill`
2. 保持目录结构不变
3. 让 Codex 读取 `SKILL.md`，并从 `references/` 中取约束

推荐 prompt：

> Use `survey-creator-skill` to generate a survey HTML page, validate the schema, render the HTML, and verify payload correctness before returning the result.

最佳实践：
- 用自然语言描述问卷目标
- 明确用户是谁、投放渠道、UI 风格、题型范围
- 让 skill 先构建内部 schema，再完成合法性校验，最后输出 HTML

---

## Claude / Claude Code 类工作流

如果你的工作流支持本地 markdown skill / prompt toolkit：

1. 保留这个仓库作为独立 repo 或本地依赖
2. 把 `SKILL.md` 当作 skill / system instruction 主体
3. 把 `references/` 当作检索材料
4. 把 `templates/` 与 `validators/` 当作辅助实现层

推荐 prompt：

> Read `SKILL.md`, generate an internal survey schema from my request, validate legality, render HTML, and only return the result if the survey is safe to deliver.

---

## Trae

对于 Trae 这类 Agent 工作流，推荐方式是：

1. 把仓库作为本地 skill / knowledge package
2. 明确让 Agent 读取 `SKILL.md`
3. 明确让 Agent 从 `references/` 获取 schema 与 logic 约束
4. 要求 Agent 先走 legality-first 流程，而不是直接根据 UI 描述吐 HTML

推荐 prompt：

> Use the local skill in `SKILL.md`. Build the survey from references, validate the schema and logic, then generate the final HTML only after checks pass.

---

## Cursor

Cursor 没有和 Codex 一样统一的 skill 规范，但这个仓库依然适合作为 Agent 辅助包使用。

推荐方式：

1. 把这个仓库和你的项目一起打开
2. 在对话里明确引用 `SKILL.md`
3. 告诉 Cursor：`references/` 是 schema / logic 的唯一约束来源
4. 不要让 Cursor 只根据 UI 描述直接出 HTML，而是先走 skill 定义的 schema → validate → render 流程

推荐 prompt：

> Follow `SKILL.md` in this repository. Use the reference files to construct a legal survey schema, validate logic and payload constraints, then output the final HTML.

---

## 示例 prompts

### 产品反馈问卷
> Use `survey-creator-skill` to create a mobile-friendly product feedback survey for AI design tool users. Include welcome, radio, checkbox, input, score, nps, and finish. Keep the UI lightweight and validate everything before returning HTML.

### 报名问卷
> Use `survey-creator-skill` to create a registration survey for kindergarten enrollment. The result should be a submittable HTML page, with schema legality and payload correctness checked before return.

### 逻辑较重的研究问卷
> Use `survey-creator-skill` to build a survey with conditional follow-up questions, manual pagination, and jump-to-page behavior. Make sure hidden/skipped questions do not enter payload.

---

## examples 目录说明

当前仓库里包含这些示例输入：

- `examples/minimal-survey.json`：最小可运行问卷示例
- `examples/ai-design-tool-demand-demo.json`：更完整的综合示例，覆盖 logic、Pagination、手动分页、一页多题、child input、score、nps
- `examples/service-satisfaction-multi-finish.json`：更接近真实业务的双结束页满意度问卷示例
- `examples/service-satisfaction-three-finish.json`：满意 / 中立 / 不满意三结束页分流示例
- `examples/service-satisfaction-post-submit-redirect.json`：更贴近真实投放的服务回访示例，覆盖多结束页 + 提交后差异化跳转

仓库中也附带了可直接打开查看的生成 HTML：

- `examples/ai-design-tool-demand-demo.html`
- `examples/service-satisfaction-multi-finish.html`
- `examples/service-satisfaction-three-finish.html`
- `examples/service-satisfaction-post-submit-redirect.html`

---

## 用户在 prompt 中最好说明什么

为了让 skill 更稳定地产出结果，用户最好在 prompt 里明确：

- 问卷目标
- 目标答题人群
- 投放渠道
- UI 风格
- 需要哪些题型
- 是否需要逻辑 / 分页 / 跳页
- 是否需要一页一题

这个 skill 最擅长的是：用户描述业务意图，仓库负责合法性约束。

---

## 性能 benchmark

当前生成 HTML 运行时的性能基准结果已归档在：

- `docs/PERFORMANCE_BENCHMARK.md`

简要结论：

- 舒适区：约 100 题 / 150 条逻辑以内
- 可用区：约 200 题 / 300 条逻辑以内
- 建议优化：300 题以上 / 400 条逻辑以上

---

## 如何使用

在支持 skill 的 Agent 环境里，直接在 prompt 中调用：

> Use `survey-creator-skill` to generate a survey HTML page, validate the schema, render the HTML, and verify payload correctness before returning the result.

如果你想要中文描述，也可以直接说明业务目标、投放渠道、UI 风格、题型要求和逻辑需求。

---

## 文档入口

- 逻辑条件与结果说明：[references/logic-condition-action-guide.md](./references/logic-condition-action-guide.md)
- toC 问卷 UI 规范：[docs/TOC_SURVEY_UI_SPEC.md](./docs/TOC_SURVEY_UI_SPEC.md)

- 英文 README：[README.md](./README.md)
- 合法性保证：[docs/LEGALITY_GUARANTEE.md](./docs/LEGALITY_GUARANTEE.md)
- 合法性矩阵：[docs/LEGALITY_MATRIX.md](./docs/LEGALITY_MATRIX.md)

---

## License

MIT
