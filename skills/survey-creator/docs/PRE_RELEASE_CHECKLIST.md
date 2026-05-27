# survey-creator-skill 上线前验收 checklist

说明：本文中的命令默认相对于 `skills/survey-creator/` 执行；如果你从仓库根目录执行，请补上 `skills/survey-creator/` 前缀。

用于确认一份由 `survey-creator-skill` 生成的问卷，是否适合真正交付给用户填写。

这份 checklist 的目标不是只覆盖“主流程能不能跑通”，而是尽量覆盖：

- 功能正确性
- 数据正确性
- 逻辑分流正确性
- 断点续答 / 重新开始
- finish / redirect 行为
- 兼容性与异常场景
- 上线前最低放行标准

---

## 0. 验收前准备
- [ ] 已固定最终 schema 输入，不再边测边改 schema
- [ ] 已确认使用的模板产物来自当前最新 `templates/base-survey-template.html`
- [ ] 已重新执行模板构建：`python3 tools/build_template.py`
- [ ] 已确认 `references/` 与 validator 版本一致
- [ ] 已安装依赖（Python / Node / Playwright）
- [ ] 已准备至少 1 份真实业务 schema，而不只是 sample schema
- [ ] 已明确投放环境：桌面浏览器 / 移动浏览器 / 微信内

---

## A. Schema 层
- [ ] schema 已生成并冻结，不再在浏览器 runtime 动态生成核心 id
- [ ] 已查看 schema validator 的语义 lint warnings，并确认没有未处理的 high severity 误用
- [ ] medium severity warning 均已人工确认可接受
- [ ] 已运行 `validate_survey_schema.py`
- [ ] 如启用自动修复，已运行 `auto_repair_survey_schema.py`
- [ ] 已确认自动修复没有改坏业务语义
- [ ] schema 校验结果为 `valid=true`
- [ ] 无 duplicate id
- [ ] 无 unsupported field
- [ ] 所有 id 都符合安全字符约束
- [ ] `survey` 为对象，`questions` 为数组，`finish` 为数组
- [ ] 所有 question type 都在支持范围内：`radio / checkbox / input / score / nps`
- [ ] 所有 child 都是 `type: input`
- [ ] 所有 child / input 的 `dataType` 都合法
- [ ] `finish` 结构合法
- [ ] 如配置多个 finish，所有 finish.id 都唯一
- [ ] 如配置 logic，所有 targetQuestionId / targetOptionId / finish target 都存在
- [ ] 如配置 `postSubmit.redirect`，其结构、URL、mode、delay 合法
- [ ] 如配置媒体资源，类型与 URL / base64 形式合法
- [ ] 如配置随机选项，题目级 / 选项级 `random` 语义明确且无冲突

---

## B. References 与字段语义一致性
- [ ] 已确认 `references/` 中每个 question json 与字段说明文档同步
- [ ] 已确认当前实现支持的字段，在 references 中都有说明
- [ ] 已确认 references 没有残留过时字段
- [ ] 已运行 `validate_reference_consistency.py`
- [ ] 当前 validator、template、SKILL 文档、references 四者描述一致
- [ ] 新增能力（如多 finish、resume、redirect）已同步到文档

---

## C. 富文本、安全与资源渲染
- [ ] rich text 已经过白名单 sanitizer
- [ ] rich text 只允许展示类元素（`div / p / span / strong / em / ul / ol / li / a / img / br / h1-h6 / blockquote` 等）
- [ ] 不允许 `script / style / iframe / form / input / button` 等元素
- [ ] link 已限制危险协议（如 `javascript:`）
- [ ] schema 注入到 HTML attribute 的值已做转义
- [ ] id / selector 相关值不会破坏 DOM 或 querySelector
- [ ] 图片按图片方式展示，不暴露资源编码细节
- [ ] 音频按音频控件展示，不暴露资源编码细节
- [ ] 视频按视频控件展示，不暴露资源编码细节
- [ ] 媒体资源加载失败时页面不会白屏
- [ ] 欢迎页 / 题目 / 结束页媒体均能独立正确展示

---

## D. HTML Runtime 层
- [ ] 已运行 `validate_survey_html_runtime.py`
- [ ] 已运行 `validate_survey_html_e2e.py`，并确认 desktop / mobile viewports 均通过
- [ ] 已运行 `validate_survey_html_interaction_e2e.py`
- [ ] 已运行 `validate_survey_html_accessibility.py`，并确认 desktop / mobile viewports 均通过
- [ ] runtime 校验结果为 `valid=true`
- [ ] E2E smoke 校验结果为 `valid=true`
- [ ] interaction E2E 结果为 `valid=true`
- [ ] accessibility 校验结果为 `valid=true`
- [ ] desktop viewport 不白屏且存在 active screen
- [ ] mobile viewport 不白屏且存在 active screen
- [ ] desktop interaction E2E 可完整填写并提交
- [ ] mobile interaction E2E 可完整填写并提交
- [ ] 所有 input / textarea / select 都有可访问名称
- [ ] 所有 button 都有可访问名称
- [ ] score / nps 按钮包含 `aria-pressed`
- [ ] 校验错误文案包含 `role="alert"` 或 `aria-live`
- [ ] 图片包含 alt，音频/视频包含 controls
- [ ] 页面存在真实 `<form>`
- [ ] 存在 `assemblePayload()`
- [ ] 存在 `validateQuestion()`
- [ ] 存在 child 显隐逻辑
- [ ] 存在 exclusive 逻辑
- [ ] 存在 mutual-exclusion 逻辑
- [ ] 存在 localStorage set/remove
- [ ] submit 会拦截并组装 payload
- [ ] 页面打开后不会白屏
- [ ] 页面无 `pageerror`
- [ ] 首屏渲染不会自动跳到错误 screen

---

## E. 题型逐项交互验收

### E1. 通用
- [ ] welcome → question → finish 流程可完整走通
- [ ] allowBack=true 时可返回上一页且数据不丢
- [ ] allowBack=false 时不会出现上一页入口
- [ ] onePageOneQuestion=true 时一次只显示一个 screen
- [ ] 非 onePageOneQuestion 模式渲染符合预期
- [ ] 手动 Pagination 模式渲染符合预期

### E2. Radio
- [ ] radio 正常单选
- [ ] radio required 校验正确
- [ ] 选中带 child 的选项后，child 正常显示
- [ ] 切换到无 child 选项后，child 正常隐藏并不残留脏数据
- [ ] radio 的随机选项渲染符合 `random` 规则

### E3. Checkbox
- [ ] checkbox 正常多选
- [ ] checkbox required 校验正确
- [ ] `exclusive=true` 的选项会清空其他项
- [ ] 先选普通项，再选 exclusive，结果正确
- [ ] 先选 exclusive，再选普通项，exclusive 会被取消
- [ ] `mutual-exclusion=true` 只会互斥同组项
- [ ] 多个 mutual-exclusion 项不会同时保留
- [ ] checkbox 带 child 的选项显隐正确
- [ ] checkbox 的随机选项渲染符合 `random` 规则

### E4. Input
- [ ] input 题型各 option 能正确渲染
- [ ] `text / email / tel / number / date / time / dateTime / dateRange / timeRange / dateTimeRange` 渲染正确
- [ ] `minLength / maxLength / required / placeholder` 约束正确
- [ ] range 类型校验正确
- [ ] 未填写 optional input 时不会误报错

### E5. Child Input
- [ ] child 可能为一个，也可能为多个，均能正确渲染
- [ ] child 的 datatype 渲染正确
- [ ] child required 校验正确
- [ ] 取消父选项后，child 数据会清理或不进入 payload

### E6. Score / NPS
- [ ] score 正常打分
- [ ] scoreDesc 会跟随当前分值正确变化
- [ ] score 题目媒体和打分项媒体渲染正确
- [ ] required 的 score 题必须所有评分行都完成
- [ ] nps 正常选择 0-10 分
- [ ] nps scoreDesc 范围文案会跟随分值正确变化
- [ ] nps 题目媒体和 scale 媒体渲染正确
- [ ] 超出 scope / step 的值不会进入合法 payload

---

## F. 逻辑与分流验收
- [ ] `show_question` 正常生效
- [ ] `hide_question` 正常生效
- [ ] `show_option` 正常生效
- [ ] `hide_option` 正常生效
- [ ] `auto_select_option` 只作用于最终可见目标
- [ ] `jump_to_question` 正常生效
- [ ] `jump_to_page` 正常生效
- [ ] `end_survey` 可跳转到指定 finish
- [ ] 多个逻辑规则同时命中时，后声明规则能正确覆盖前者
- [ ] 被隐藏题不会阻断 required 校验
- [ ] 被隐藏题不会进入 payload
- [ ] 被跳过题不会进入 payload
- [ ] 被隐藏题会从缓存中清除
- [ ] 被隐藏选项会从状态中清除
- [ ] 逻辑切换来回反复触发时，页面不会错乱
- [ ] 恢复缓存后重新计算逻辑，结果与首次填写一致
- [ ] 分流到不同 finish 时，页面与提交数据都正确

---

## G. 多结束页 / 提交后跳转验收
- [ ] 单 finish 问卷可正常提交
- [ ] 多 finish 问卷可根据逻辑进入正确 finish
- [ ] finish 页仅展示当前分支对应的内容
- [ ] submit 按钮文案符合 finish 配置
- [ ] finish 提示文案符合 finish 配置
- [ ] 未配置 redirect 时，提交成功后只结束问卷、不误跳转
- [ ] 配置 `postSubmit.redirect.mode=immediate` 时，提交成功后立即跳转
- [ ] 配置 `postSubmit.redirect.mode=delay` 时，提交成功后显示倒计时并延迟跳转
- [ ] delay 模式下“立即前往”按钮可用
- [ ] redirect 一定发生在提交成功之后，而不是之前
- [ ] redirect 不会导致 payload 丢失
- [ ] 不同 finish 可对应不同 redirect URL
- [ ] `openIn=self` 与 `openIn=blank` 表现正确

---

## H. 断点续答 / 重新开始 / 本地缓存
- [ ] 第一次打开问卷，不出现断点续答弹层
- [ ] 刷新页面后，如存在有效缓存，出现断点续答弹层
- [ ] 重新访问页面后，如存在有效缓存，出现断点续答弹层
- [ ] 出现弹层前，页面停留在欢迎页，不自动跳到中间题目
- [ ] 弹层文案正确：`继续上次作答 / 重新开始作答`
- [ ] 点击“继续上次作答”后，回到上次离开的 screen
- [ ] 点击“继续上次作答”后，已填答案正确回填
- [ ] 点击“重新开始作答”后，缓存被清空
- [ ] 点击“重新开始作答”后，回到欢迎页
- [ ] 恢复后继续作答，逻辑分流仍正确
- [ ] 恢复后提交，payload 正确
- [ ] 重新开始后提交，payload 不包含旧数据
- [ ] 提交成功后 localStorage 已清空
- [ ] 非法 `lastScreenId` 不会导致白屏，应兜底回到欢迎页
- [ ] 旧缓存结构不完整时不会导致白屏
- [ ] 缓存中的 hidden / skipped 数据不会被错误恢复
- [ ] schema 变更后，如旧缓存不再兼容，不会造成错误提交

---

## I. Payload 层
- [ ] 已运行 `validate_survey_payload.py`
- [ ] 已运行 `validate_payload_against_schema.py`，确认 payload 与具体 schema 完全匹配
- [ ] 已确认浏览器真实提交 payload 也经过 `payload-against-schema` 校验
- [ ] payload 校验结果为 `valid=true`
- [ ] 顶层包含 `surveyId / submittedAt / answers`
- [ ] 未作答题不会出现在 `answers`
- [ ] `radio.value` 为对象
- [ ] `checkbox.value` 为数组
- [ ] `input.value` 为数组
- [ ] `score.value` 为数组
- [ ] `nps.value` 为对象，包含 `optionId / score`
- [ ] child 为数组
- [ ] range value 为 `{start, end}`
- [ ] `questionId` 在 `answers` 中不重复
- [ ] `payload.surveyId` 与 `schema.survey.id` 一致
- [ ] 每个 `answer.questionId` 都存在于 `schema.questions`
- [ ] 每个 `answer.questionType` 都与 schema 中的问题类型一致
- [ ] 每个 `optionId / childId` 都存在于对应问题/选项下
- [ ] required question 均出现在 answers 中
- [ ] score / nps 分值均落在 schema.scope 和 step 约束内
- [ ] checkbox payload 不包含 exclusive 与其他选项共存的非法组合
- [ ] checkbox payload 不包含多个 mutual-exclusion 选项共存的非法组合
- [ ] 被隐藏 / 被跳过题目不进入 payload
- [ ] finish / redirect 配置不会污染 payload 结构

---

## J. 兼容性与真实环境验收
- [ ] Chrome 桌面端正常
- [ ] Safari 桌面端正常（如投放到 Apple 生态建议必测）
- [ ] iPhone Safari 正常
- [ ] Android Chrome 正常
- [ ] 微信内 H5 环境正常
- [ ] PC 微信内打开正常（如目标场景包含 PC 微信）
- [ ] 不同 viewport 下布局无严重错位
- [ ] 长标题 / 长描述 / 长选项文案不会溢出破版
- [ ] 欢迎页 / 题目页 / finish 页媒体在移动端比例正常
- [ ] 弹层在移动端不会超出可视区
- [ ] 键盘弹出时输入题可正常填写

---

## K. 异常注入与边界场景
- [ ] localStorage 被禁用时，页面仍可填写与提交（至少不白屏）
- [ ] localStorage quota exceeded 时，不会导致页面主流程崩溃
- [ ] 手动污染缓存结构后，页面仍能安全兜底
- [ ] 同一问卷开两个 tab，同步行为不会造成明显异常
- [ ] 一个 tab 作答、另一个 tab 刷新，不会导致错误提交旧数据
- [ ] 浏览器后退 / 前进行为不会让问卷状态错乱
- [ ] 刷新发生在 delay redirect 倒计时中时，行为可接受
- [ ] 网络很慢 / 媒体加载慢时，页面不白屏
- [ ] 恶意 schema 内容不会造成可见 XSS 或 DOM 断裂

---

## L. 自动化回归命令
- [ ] 已执行：`python3 tools/build_template.py`
- [ ] 已执行：`python3 validators/validate_reference_consistency.py`
- [ ] 已执行：`python3 tests/contract/run_contract_tests.py`
- [ ] 已执行：`bash validators/run-validator-smoke-tests.sh`
- [ ] 如需一键总回归，已执行：`bash run_all_legality_checks.sh`

---

## M. 交付判定

### 可交付给用户填写的最低标准
- [ ] pipeline report 中 `releaseDecision.shipReady === true`
- [ ] pipeline report 中 `payloadAgainstSchema.valid === true`
- [ ] pipeline report 中 `browserPayloadAgainstSchema.valid === true`
- [ ] pipeline report 中 `htmlE2E.viewports.desktop.valid === true`
- [ ] pipeline report 中 `htmlE2E.viewports.mobile.valid === true`
- [ ] pipeline report 中 `htmlInteractionE2E.viewports.desktop.valid === true`
- [ ] pipeline report 中 `htmlInteractionE2E.viewports.mobile.valid === true`
- [ ] pipeline report 中 `htmlAccessibility.valid === true`
- [ ] pipeline report 中 `htmlAccessibility.viewports.desktop.valid === true`
- [ ] pipeline report 中 `htmlAccessibility.viewports.mobile.valid === true`
- [ ] A / D / F / H / I 至少全部通过
- [ ] 高风险真实业务 schema 已人工走查
- [ ] 无 schema error
- [ ] 无 payload error
- [ ] 无 runtime error
- [ ] `manualReviewRequired` 项已人工确认

### 不建议上线的情况
- [ ] 任意 validator 返回 non-zero
- [ ] rich text 未做 sanitizer
- [ ] schema id 仍在 runtime 动态生成
- [ ] 关键交互（`exclusive / child / range / resume / redirect / cache`）未验证
- [ ] payload shape 与 contract 不一致
- [ ] 浏览器真实提交 payload 未做 against-schema 校验
- [ ] 多 finish / redirect 虽配置但未走查真实场景

---

## 建议流程
1. 先跑 schema validator
2. 再生成 HTML
3. 再跑 runtime / E2E / accessibility / interaction 校验
4. 再做手工交互验证
5. 导出 payload 样例并跑 payload validator
6. 跑 payload-against-schema validator，确认回收数据不会引用不存在的 id 或越界分值
7. 覆盖断点续答 / 重新开始 / redirect / 多 finish 场景
8. 通过后再给用户填写

也可以直接使用统一入口：

```bash
python3 <survey-creator-root>/validators/run_survey_creator_pipeline.py \
  --schema /absolute/path/to/schema.json \
  --output-dir /absolute/path/to/output-dir \
  --auto-repair \
  --fail-on-high-warning
```

只有当：

- `releaseDecision.shipReady === true`
- `payloadAgainstSchema.valid === true`
- `browserPayloadAgainstSchema.valid === true`

三者同时满足时，才允许交付 HTML。
