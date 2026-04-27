# survey-creator-skill

[English](./README.md) | [简体中文](./README.zh-CN.md)

**An AI-agent-ready survey generation skill for teams that want fully custom UI, independent deployment, and validated HTML output.**

`survey-creator-skill` is an open-source skill repository for **Claude Code, Codex, Cursor, Trae, and similar AI coding agent workflows**.

It was created for one very specific reason:

> mainstream survey platforms are good at centralized management, but weak at **AI-native creation, UI freedom, and independently deployable survey delivery**.

If you have ever used hosted survey platforms, the pain is familiar:

- AI can help a little, but it is usually not the default workflow
- UI is mostly theme-based, not truly custom
- every survey is still shaped by the platform
- even a one-question page may carry a platform-heavy runtime
- the final payload and logic behavior are often hard to verify precisely

This skill takes a different path:

- generate survey schema from natural-language intent
- validate legality before delivery
- render **fully customizable HTML survey pages**
- verify runtime behavior, interaction flow, accessibility, and payload correctness
- let every survey be delivered as an **independent artifact**, not a platform-bound page

If you want AI to generate questionnaires **without silently producing invalid forms, broken payloads, or locked-in platform UI**, this project is built for that.

---

## Why not just use a survey platform?

| Capability | Traditional survey platforms | survey-creator-skill |
|---|---|---|
| AI-native workflow | Usually limited | Yes |
| Fully custom UI | Usually limited to themes / skins | Yes |
| Independent deployment | Usually platform-shaped | Yes |
| One-question lightweight delivery | Often inefficient | Good fit |
| Branch-specific endings and redirects | Limited flexibility | Native |
| Payload validation against concrete schema | Usually opaque | Yes |
| Brand-consistent landing-page style survey | Hard | Native |

---

## Why this exists

This project was not started to build “another survey tool”.

It was started because many existing survey platforms are still weak in three places:

### 1. AI-native creation is weak
Most tools still behave like:

- traditional form builder
- plus one extra AI button

That is very different from:

- describe intent
- let AI generate the survey structure
- validate it automatically
- render a deployable page

### 2. UI freedom is weak
In many hosted platforms, you can:

- choose a template
- switch a skin
- adjust a few colors

But you usually **cannot** truly design the survey like:

- a branded landing page
- a campaign conversion page
- a product-native flow
- a one-question embedded experience

### 3. Delivery is too centralized
In many platforms, the survey page is still owned by the platform:

- platform-shaped runtime
- platform-shaped page structure
- limited deployment flexibility
- heavier than necessary for small survey experiences

`survey-creator-skill` exists to make surveys feel more like **frontend artifacts** than centralized hosted forms.

---

## Who this is for

This skill is especially useful for:

- teams with frontend engineering ability
- teams with strong brand / UI requirements
- teams that want surveys to be independently deployed
- teams that want AI to directly output working pages
- teams that are no longer satisfied with template-based survey platforms

If your team wants the output to look and behave like **your product**, not like a survey vendor page, this repository is likely a good fit.

---

## What problem it solves

`survey-creator-skill` is designed for teams that want:

- **fully custom survey UI**
- **independent survey delivery**
- **schema-constrained AI generation**
- **browser-testable survey runtime**
- **validated submit payloads**
- **logic-safe branching behavior**

Instead of only producing “some JSON” or “some HTML”, it gives agents a stricter workflow:

1. understand the business intent
2. generate schema from references
3. validate schema legality
4. render HTML from the validated schema
5. validate runtime and interaction behavior
6. validate payload against the concrete schema
7. return only shippable output

That is what makes it useful for real delivery.

---

## What this is not

`survey-creator-skill` is **not** a full survey SaaS.

It does not try to replace:

- survey management backends
- reporting dashboards
- org / permission systems
- no-code operations consoles
- hosted survey platforms for non-technical teams

Its focus is narrower and more intentional:

- schema
- runtime
- validation
- HTML artifact output

In short:

> this project is about **survey generation and delivery**, not survey operations software.

---

## Best use cases

- AI-generated surveys
- registration questionnaires
- screening / qualification forms
- customer satisfaction research
- NPS / score workflows
- AI Native form creation flows
- branded campaign surveys
- independently deployable one-question or lightweight survey pages
- teams that need stronger legality guardrails before shipping HTML questionnaires

---

## Quick start with AI coding agents

This repository is primarily meant to be used as a **skill** inside agent products, not as a standalone script-first toolkit.

Recommended environments:

- Codex
- Claude / Claude Code style local skills
- Trae
- Cursor

Typical prompt:

> Use `survey-creator-skill` to generate a survey HTML page, validate the schema, render the HTML, and verify payload correctness before returning the result.

Best practice:

- describe the survey goal in plain language
- describe respondent type, delivery channel, UI style, and question families
- let the skill build an internal schema first, then validate before returning HTML

For technical setup, supported node types, logic rules, and runtime details, see:

- [docs/TECHNICAL_DETAILS.md](./docs/TECHNICAL_DETAILS.md)

---

## Example files

The repository currently includes these example inputs in `examples/`:

- `minimal-survey.json` — the smallest valid survey example
- `ai-design-tool-demand-demo.json` — a richer demo covering logic, Pagination, multi-question pages, child input, score, and nps
- `service-satisfaction-multi-finish.json` — a more production-like satisfaction flow with branch-specific ending pages
- `service-satisfaction-three-finish.json` — a three-ending example for positive / neutral / negative user branches
- `service-satisfaction-post-submit-redirect.json` — a real-world service callback demo with branch-specific finish pages and different post-submit redirects
- `lead-qualification-sales-conversion.json` — a real-world sales qualification demo with hot / consult / nurture / self-serve branches

Generated HTML examples are also checked in for direct inspection and browser testing, including:

- `examples/ai-design-tool-demand-demo.html`
- `examples/service-satisfaction-multi-finish.html`
- `examples/service-satisfaction-three-finish.html`
- `examples/service-satisfaction-post-submit-redirect.html`
- `examples/lead-qualification-sales-conversion.html`

---

## More docs

- Technical details: [docs/TECHNICAL_DETAILS.md](./docs/TECHNICAL_DETAILS.md)
- Logic condition and action guide: [references/logic-condition-action-guide.md](./references/logic-condition-action-guide.md)
- toC survey UI spec: [docs/TOC_SURVEY_UI_SPEC.md](./docs/TOC_SURVEY_UI_SPEC.md)
- Legality guarantee: [docs/LEGALITY_GUARANTEE.md](./docs/LEGALITY_GUARANTEE.md)
- Legality matrix: [docs/LEGALITY_MATRIX.md](./docs/LEGALITY_MATRIX.md)
- Pre-release checklist: [docs/PRE_RELEASE_CHECKLIST.md](./docs/PRE_RELEASE_CHECKLIST.md)
- Performance benchmark: [docs/PERFORMANCE_BENCHMARK.md](./docs/PERFORMANCE_BENCHMARK.md)

---

## License

MIT
