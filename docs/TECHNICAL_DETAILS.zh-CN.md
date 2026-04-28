# 技术细节

这份文档承接所有偏实现层、校验层、运行层的内容，避免 README 首页过度技术化。

---

## 当前支持的题型 / 节点

- `radio`
- `checkbox`
- `input`
- `score`
- `nps`
- `survey`
- `finish`
- `Pagination`

## 当前支持的 toC 风格包

- `consumer-minimal`
- `consumer-polished`
- `consumer-trust`
- `consumer-editorial`
- `consumer-utility`
- `consumer-campaign`

---

## 当前支持的逻辑操作符

- `selected`
- `not_selected`
- `contains`
- `not_contains`
- `exists`
- `not_exists`
- `answered`
- `not_answered`
- `eq`
- `neq`
- `gt`
- `lt`

## 当前支持的逻辑动作

- `show_question`
- `hide_question`
- `show_option`
- `hide_option`
- `auto_select_option`
- `jump_to_question`
- `jump_to_page`
- `end_survey`

---

## 逻辑保证

当前运行时已经保证：

- **hidden = 不存在**
- **skipped = 不存在**
- 被隐藏 / 跳过的题目不会阻断 required 校验
- 被隐藏 / 跳过的题目不会进入 payload
- 被隐藏 / 跳过的题目会从 cache 中清除
- 被隐藏的选项会从状态中清除
- 逻辑冲突按声明顺序解析
- 后匹配的规则会覆盖前匹配的规则
- auto-select 只作用于最终可见目标
- `end_survey` 可以指向具体的 `finish[].id`
- 支持多结束页，用于不同分支结束态
- 每个 `finish[]` 可以可选配置 `postSubmit.redirect`
- redirect 只会在“提交成功后”执行，不会绕过问卷结果回收

---

## 断点续答与重新开始

当用户刷新 / 重新访问问卷，并且本地已经存在上一轮页面生命周期留下的 step cache 时，生成的 HTML 现在支持真正的断点续答：

- 用户第一次进入问卷时，不会出现断点选择弹层
- 用户刷新 / 再次访问且已有保存进度时，会看到两个选项：
  - **重新开始作答**
  - **继续上次作答**
- 选择继续时，会回到上次离开的那一屏继续填写
- 选择重新开始时，会清空本地缓存并回到问卷开头
- 这套能力建立在已有的 localStorage 步进缓存之上

---

## skill 仓库结构

```text
survey-creator-skill/
  SKILL.md                    # Agent 读取的主 skill 定义
  README.md                   # 英文说明
  README.zh-CN.md             # 中文说明
  docs/                       # 给人看的文档
  references/                 # 给模型读取的 schema / logic 约束
  templates/                  # HTML 模板资源
  validators/                 # 校验与渲染辅助层
  examples/                   # 示例 schema 与 HTML
  tests/                      # contract tests
  evals/                      # 评估样例
  LICENSE
```

---

## 运行依赖

这个 skill 可以开源复用，但它**不是零依赖**的。

如果要完整跑通「schema 校验 → HTML 渲染 → 浏览器 E2E / 交互校验 → payload 校验」这条链路，目标环境需要具备：

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

最终单文件产物输出到：

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

如果只是把这个仓库当作 Agent 的检索材料使用，只读取这些内容：

- `SKILL.md`
- `references/`
- `templates/`

那么可以先不跑完整依赖。

但如果希望这个 skill 真正执行合法性校验并输出可交付结果，就应先安装上面的依赖。

---

## 在 AI Agent / IDE 中使用

这个仓库的主定位是：**作为 skill 给 Codex、Claude Code、OpenCode 等 Agent 使用**，而不是优先面向“手工执行脚本”的独立工具。

推荐环境：

- Claude Code
- Codex
- OpenCode

### Codex

推荐方式：

1. 先把仓库发布到公开 GitHub
2. 使用下面的方式安装：

```bash
npx skills add piter902/survey-creator-skill -a codex
```

3. 让 Codex 读取 `SKILL.md`，并从 `references/` 中取约束

如果你想先验证仓库能否被正确识别：

```bash
npx skills add https://github.com/piter902/survey-creator-skill --list
```

推荐 prompt：

> Use `survey-creator-skill` to generate a survey HTML page, validate the schema, render the HTML, and verify payload correctness before returning the result.

最佳实践：
- 用自然语言描述问卷目标
- 明确用户是谁、投放渠道、UI 风格、题型范围
- 让 skill 先构建内部 schema，再完成合法性校验，最后输出 HTML

### Claude / Claude Code 类工作流

推荐方式：

```bash
npx skills add piter902/survey-creator-skill -a claude-code
```

然后：

1. 把 `SKILL.md` 当作 skill / system instruction 主体
2. 把 `references/` 当作检索材料
3. 把 `templates/` 与 `validators/` 当作辅助实现层

推荐 prompt：

> Read `SKILL.md`, generate an internal survey schema from my request, validate legality, render HTML, and only return the result if the survey is safe to deliver.

### OpenCode

推荐方式：

```bash
npx skills add piter902/survey-creator-skill -a opencode
```

然后：

1. 明确让 Agent 读取 `SKILL.md`
2. 明确让 Agent 从 `references/` 获取 schema 与 logic 约束
3. 要求 Agent 先走 legality-first 流程，而不是直接根据 UI 描述吐 HTML

推荐 prompt：

> Use the local skill in `SKILL.md`. Build the survey from references, validate the schema and logic, then generate the final HTML only after checks pass.

---

## 示例 prompts

### 产品反馈问卷
> Use `survey-creator-skill` to create a mobile-friendly product feedback survey for AI design tool users. Include welcome, radio, checkbox, input, score, nps, and finish. Keep the UI lightweight and validate everything before returning HTML.

### 报名问卷
> Use `survey-creator-skill` to create a registration survey for kindergarten enrollment. The result should be a submittable HTML page, with schema legality and payload correctness checked before return.

### 逻辑较重的研究问卷
> Use `survey-creator-skill` to build a survey with conditional follow-up questions, manual pagination, and jump-to-page behavior. Make sure hidden/skipped questions do not enter payload.

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

## 更多文档

- 逻辑条件与结果说明：`references/logic-condition-action-guide.md`
- toC 问卷 UI 规范：`docs/TOC_SURVEY_UI_SPEC.md`
- 合法性保证：`docs/LEGALITY_GUARANTEE.md`
- 合法性矩阵：`docs/LEGALITY_MATRIX.md`
- 上线前检查清单：`docs/PRE_RELEASE_CHECKLIST.md`
