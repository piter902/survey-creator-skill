# survey-creator-skill

[English](./README.md) | 简体中文

**一个面向 Codex、Claude Code、OpenCode 等 AI Agent 工作流的问卷生成 skill：支持完全自定义 UI、独立部署、以及可校验的 HTML 交付。**

`survey-creator-skill` 是一个开源的 **问卷 skill suite 仓库**。目标不是再做一个传统问卷平台，而是让 AI Agent 可以把自然语言需求转成：

当前结构：

- `skills/survey-creator/`：问卷生成 skill
- `skills/survey-analytics/`：问卷分析 skill
- `specs/`：由使用方自己实现的后端 / 托管 / 存储接入规范

核心产物：

- 合法的问卷 schema
- 可提交的 HTML 问卷页面
- 可校验的交互与 payload
- 可独立部署的 survey artifact

这个项目的出发点很直接：

> 现有很多问卷平台擅长集中式管理，但在 **AI Native 创建、UI 自由度、独立交付** 这三件事上依然不够强。

很多团队会遇到这些问题：

- AI 只是附加功能，不是默认工作流
- UI 多数只能换皮肤，不能真正自定义
- 问卷页面依然带着平台形态
- 即使只做一道题，也常常要加载整套平台式资源
- 提交结果和逻辑链路很难做严格校验

`survey-creator-skill` 走的是另一条路：

- 从自然语言意图生成问卷 schema
- 在交付前先做合法性校验
- 生成 **完全可自定义 UI 的 HTML 问卷页面**
- 校验运行时、交互、可访问性、payload 正确性
- 让每一份问卷都成为 **独立产物**，而不是平台托管页面
- 只定义后端接入协议，不把托管和存储强绑定到仓库本身

如果你希望 AI 生成问卷时，**不是只出一个能看但不一定能交付的页面**，而是得到一套可校验、可提交、可独立部署、可回收数据的结果，这个项目就是为此设计的。

---

## 为什么不直接用传统问卷平台？

| 能力维度 | 传统问卷平台 | survey-creator-skill |
|---|---|---|
| AI Native 工作流 | 通常较弱 | 支持 |
| 完全自定义 UI | 通常只支持主题 / 皮肤 | 支持 |
| 独立部署 | 通常仍然带平台形态 | 支持 |
| 单题 / 轻量问卷交付 | 往往不够轻 | 更适合 |
| 分支结束页与差异化跳转 | 灵活度有限 | 原生支持 |
| 基于具体 schema 的 payload 校验 | 通常不透明 | 支持 |
| 品牌化落地页式问卷 | 难做到彻底一致 | 原生适合 |

---

## 为什么要做这个 skill

我开发这个 skill，并不是为了“再做一个问卷工具”。

而是因为主流问卷平台在三件事情上普遍不够理想：

### 1. AI Native 创建能力弱
很多工具更像：

- 传统表单编辑器
- 外挂一个 AI 按钮

而不是：

- 先描述业务意图
- 再由 AI 生成问卷结构
- 自动完成校验
- 最后直接输出可交付页面

### 2. UI 自由度弱
很多平台支持的是：

- 模板
- 主题
- 皮肤

但不是真正的：

- 品牌化页面设计
- 活动落地页式问卷
- 产品内嵌式一题反馈
- 完整自定义结构与交互

### 3. 问卷交付过于中心化
很多平台即使只做一个轻量问卷，最终页面仍然：

- 依赖平台式运行时
- 保留平台式页面结构
- 部署自由度有限
- 对小问卷或单题场景来说偏重

所以 `survey-creator-skill` 的核心不是“托管问卷”，而是把问卷变成一种 **可生成、可校验、可独立部署的前端资产**。

---

## 适合哪些团队

这个 skill 特别适合：

- 有前端能力的团队
- 有品牌 / UI 要求的团队
- 希望问卷独立部署的团队
- 希望 AI 直接产出页面的团队
- 不满足于“套模板问卷平台”的团队

如果你的团队希望问卷看起来像 **你自己的产品页面**，而不是某个问卷平台页面，这个项目会非常适合。

---

## 这个 skill 解决什么问题

`survey-creator-skill` 重点解决的是：

- **完全自定义问卷 UI**
- **问卷独立交付与部署**
- **schema 约束下的 AI 生成**
- **浏览器可运行、可测试的问卷 runtime**
- **可验证的提交 payload**
- **可控的逻辑分流与结束页跳转**

它不是只做：

- 生成一份 JSON
- 渲染一份 HTML
- 然后假设提交数据没问题

而是给 Agent 一条更严格的工作流：

1. 理解业务意图
2. 基于 references 生成 schema
3. 校验 schema 合法性
4. 基于合法 schema 生成 HTML
5. 校验运行时与交互
6. 校验 payload 与具体 schema 一一对应
7. 只返回可交付结果

这也是它真正适合业务场景的原因。

---

## 它不是什么

`survey-creator-skill` **不是** 一个完整的问卷 SaaS。

它并不试图替代：

- 问卷管理后台
- 报表分析系统
- 用户 / 组织 / 权限体系
- 面向非技术团队的零代码运营平台

它更专注的是：

- schema
- runtime
- validation
- HTML artifact 输出
- 分析输入输出协议

换句话说：

> 这个项目做的是 **问卷生成与分析协议层**，不是完整的问卷运营平台。

---

## skill 模型

这个仓库当前只保留两个核心 skill：

- `survey-creator`
- `survey-analytics`

至于怎么上传 HTML / schema、怎么保存答案、怎么提供访问 URL，这些都交给使用这个开源仓库的团队自己实现，仓库只负责在 `specs/` 里把协议定义清楚。

---

## 适合哪些场景

- AI 生成问卷
- 满意度调查
- 报名问卷
- 用户研究
- 产品反馈收集
- 筛选 / 分流式问卷
- NPS / 评分 / 调研场景
- 品牌化活动问卷
- 独立部署的轻量问卷 / 单题问卷

---

## 如何在 AI Agent 中快速使用

这个仓库的主定位是：**作为 skill 给 Codex、Claude Code、OpenCode 等 Agent 使用**，而不是优先面向“手工执行脚本”的独立工具。

推荐环境：

- Claude Code
- Codex
- OpenCode

### 通过 skills.sh / `npx skills` 安装

推荐的安装方式，是直接通过 `npx skills add` 从 GitHub 安装，而不是手动 clone 到本地 skills 目录。

```bash
npx skills add piter902/survey-creator-skill
```

也可以指定目标 Agent：

```bash
npx skills add piter902/survey-creator-skill -a claude-code
npx skills add piter902/survey-creator-skill -a codex
npx skills add piter902/survey-creator-skill -a opencode
```

推荐 prompt：

> Use `survey-creator-skill` to generate a survey HTML page, validate the schema, render the HTML, and verify payload correctness before returning the result.

分析类 prompt：

> Use `survey-analytics` to analyze a survey schema plus answer dataset and return key findings, segment patterns, and recommendations.

现在 `survey-analytics` 已经不只是输出文字分析，还可以直接生成：

- 一份带平铺答卷和图表的 Excel
- 一份机器可读的 analysis JSON
- 一份 markdown 洞察报告

最佳实践：

- 用自然语言描述问卷目标
- 明确用户是谁、投放渠道、UI 风格、题型范围
- 让 skill 先构建内部 schema，再完成合法性校验，最后输出 HTML

技术细节、依赖、校验链路、支持范围请看：

- [skills/survey-creator/docs/TECHNICAL_DETAILS.zh-CN.md](./skills/survey-creator/docs/TECHNICAL_DETAILS.zh-CN.md)

---

## examples 目录说明

当前仓库里包含这些示例输入，位置都在 `skills/survey-creator/examples/`：

- `skills/survey-creator/examples/minimal-survey.json`：最小可运行问卷示例
- `skills/survey-creator/examples/ai-design-tool-demand-demo.json`：更完整的综合示例，覆盖 logic、Pagination、手动分页、一页多题、child input、score、nps
- `skills/survey-creator/examples/service-satisfaction-multi-finish.json`：更接近真实业务的双结束页满意度问卷示例
- `skills/survey-creator/examples/service-satisfaction-three-finish.json`：满意 / 中立 / 不满意三结束页分流示例
- `skills/survey-creator/examples/service-satisfaction-post-submit-redirect.json`：更贴近真实投放的服务回访示例，覆盖多结束页 + 提交后差异化跳转
- `skills/survey-creator/examples/lead-qualification-sales-conversion.json`：线索筛选 / 销售转化型示例，覆盖热线索、咨询、培育、自助资源四类分流

仓库中也附带了可直接打开查看的生成 HTML：

- `skills/survey-creator/examples/ai-design-tool-demand-demo.html`
- `skills/survey-creator/examples/service-satisfaction-multi-finish.html`
- `skills/survey-creator/examples/service-satisfaction-three-finish.html`
- `skills/survey-creator/examples/service-satisfaction-post-submit-redirect.html`
- `skills/survey-creator/examples/lead-qualification-sales-conversion.html`

---

## 更多文档

- 技术细节：[skills/survey-creator/docs/TECHNICAL_DETAILS.zh-CN.md](./skills/survey-creator/docs/TECHNICAL_DETAILS.zh-CN.md)
- 问卷分析产物说明：[skills/survey-analytics/docs/OUTPUTS.md](./skills/survey-analytics/docs/OUTPUTS.md)
- 逻辑条件与结果说明：[skills/survey-creator/references/logic-condition-action-guide.md](./skills/survey-creator/references/logic-condition-action-guide.md)
- toC 问卷 UI 规范：[skills/survey-creator/docs/TOC_SURVEY_UI_SPEC.md](./skills/survey-creator/docs/TOC_SURVEY_UI_SPEC.md)
- 合法性保证：[skills/survey-creator/docs/LEGALITY_GUARANTEE.md](./skills/survey-creator/docs/LEGALITY_GUARANTEE.md)
- 合法性矩阵：[skills/survey-creator/docs/LEGALITY_MATRIX.md](./skills/survey-creator/docs/LEGALITY_MATRIX.md)
- 上线前检查清单：[skills/survey-creator/docs/PRE_RELEASE_CHECKLIST.md](./skills/survey-creator/docs/PRE_RELEASE_CHECKLIST.md)
- 性能 benchmark：[skills/survey-creator/docs/PERFORMANCE_BENCHMARK.md](./skills/survey-creator/docs/PERFORMANCE_BENCHMARK.md)
- 问卷 bundle 协议：[specs/survey-bundle.md](./specs/survey-bundle.md)
- specs 总览：[specs/README.md](./specs/README.md)
- 提交接口协议：[specs/submission-api.md](./specs/submission-api.md)
- 问卷文件保存协议：[specs/survey-file-storage.md](./specs/survey-file-storage.md)
- 答案存储协议：[specs/answer-storage.md](./specs/answer-storage.md)
- 分析输入协议：[specs/analytics-input.md](./specs/analytics-input.md)
- 最小后端接入示例：[specs/minimal-backend-example.md](./specs/minimal-backend-example.md)
- 集成验收清单：[specs/integration-checklist.md](./specs/integration-checklist.md)

---

## License

MIT
