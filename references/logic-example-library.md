# Logic example library

This file provides reusable logic patterns for common survey behaviors.

Use these examples as composition templates when generating new schema.

---

## 1. Show a follow-up question after a selected option

```json
{
  "id": "logic_show_followup",
  "when": {
    "questionId": "question_entry",
    "operator": "selected",
    "optionId": "option_yes"
  },
  "action": {
    "type": "show_question",
    "targetQuestionId": "question_followup"
  }
}
```

---

## 2. Hide a question for a fast path

```json
{
  "id": "logic_hide_detail",
  "when": {
    "questionId": "question_mode",
    "operator": "selected",
    "optionId": "option_fast"
  },
  "action": {
    "type": "hide_question",
    "targetQuestionId": "question_detail"
  }
}
```

---

## 3. Show an advanced option only for matched users

```json
{
  "id": "logic_show_advanced_option",
  "when": {
    "questionId": "question_tier",
    "operator": "selected",
    "optionId": "option_pro"
  },
  "action": {
    "type": "show_option",
    "targetQuestionId": "question_package",
    "targetOptionId": "option_advanced"
  }
}
```

---

## 4. Hide an incompatible option

```json
{
  "id": "logic_hide_manual_option",
  "when": {
    "questionId": "question_need_ai",
    "operator": "selected",
    "optionId": "option_need_ai_yes"
  },
  "action": {
    "type": "hide_option",
    "targetQuestionId": "question_modes",
    "targetOptionId": "option_manual"
  }
}
```

---

## 5. Auto-select a recommended option

```json
{
  "id": "logic_auto_select_ai",
  "when": {
    "questionId": "question_need_ai",
    "operator": "selected",
    "optionId": "option_need_ai_yes"
  },
  "action": {
    "type": "auto_select_option",
    "targetQuestionId": "question_modes",
    "targetOptionId": "option_ai"
  }
}
```

---

## 6. Jump to a target question

```json
{
  "id": "logic_jump_to_budget",
  "when": {
    "questionId": "question_role",
    "operator": "selected",
    "optionId": "option_buyer"
  },
  "action": {
    "type": "jump_to_question",
    "targetQuestionId": "question_budget"
  }
}
```

---

## 7. Jump to a page

```json
{
  "id": "logic_jump_to_summary_page",
  "when": {
    "questionId": "question_route",
    "operator": "selected",
    "optionId": "option_fast"
  },
  "action": {
    "type": "jump_to_page",
    "targetQuestionId": "question_summary"
  }
}
```

---

## 8. End survey early

```json
{
  "id": "logic_end_early",
  "when": {
    "questionId": "question_qualified",
    "operator": "selected",
    "optionId": "option_not_qualified"
  },
  "action": {
    "type": "end_survey"
  }
}
```

---

## 8.1. Route different users to different finish screens

```json
{
  "id": "logic_satisfied_to_positive_finish",
  "when": {
    "questionId": "question_satisfaction",
    "operator": "selected",
    "optionId": "option_satisfied"
  },
  "action": {
    "type": "end_survey",
    "targetQuestionId": "finish_positive"
  }
}
```

```json
{
  "id": "logic_unsatisfied_to_care_finish",
  "when": {
    "questionId": "question_callback_permission",
    "operator": "selected",
    "optionId": "option_callback_no"
  },
  "action": {
    "type": "end_survey",
    "targetQuestionId": "finish_care"
  }
}
```

Best practice:
- Keep the first `finish[]` item as the default/general finish.
- Use `end_survey.targetQuestionId` only for finish ids, not normal question ids.
- If a branch needs extra data first, collect those follow-up questions before firing `end_survey`.
- Prefer one finish screen per emotional outcome, such as thank-you / qualification passed / apology and follow-up.

---

## 9. Text contains

```json
{
  "id": "logic_contains_keyword",
  "when": {
    "questionId": "question_feedback",
    "operator": "contains",
    "value": "价格"
  },
  "action": {
    "type": "show_question",
    "targetQuestionId": "question_price_followup"
  }
}
```

---

## 10. Text not contains

```json
{
  "id": "logic_not_contains_keyword",
  "when": {
    "questionId": "question_feedback",
    "operator": "not_contains",
    "value": "无需联系"
  },
  "action": {
    "type": "show_question",
    "targetQuestionId": "question_contact_permission"
  }
}
```

---

## 11. Equals / not equals

```json
{
  "id": "logic_eq_exact_code",
  "when": {
    "questionId": "question_code",
    "operator": "eq",
    "value": "VIP"
  },
  "action": {
    "type": "show_question",
    "targetQuestionId": "question_vip_path"
  }
}
```

```json
{
  "id": "logic_neq_exact_code",
  "when": {
    "questionId": "question_code",
    "operator": "neq",
    "value": "VIP"
  },
  "action": {
    "type": "show_question",
    "targetQuestionId": "question_normal_path"
  }
}
```

---

## 12. Greater than / less than

```json
{
  "id": "logic_gt_age",
  "when": {
    "questionId": "question_age",
    "operator": "gt",
    "value": 18
  },
  "action": {
    "type": "show_question",
    "targetQuestionId": "question_adult_flow"
  }
}
```

```json
{
  "id": "logic_lt_budget",
  "when": {
    "questionId": "question_budget",
    "operator": "lt",
    "value": 100
  },
  "action": {
    "type": "show_question",
    "targetQuestionId": "question_budget_sensitive"
  }
}
```

---

## 13. Exists / not exists

```json
{
  "id": "logic_exists_tags",
  "when": {
    "questionId": "question_tags",
    "operator": "exists",
    "optionIds": ["option_a", "option_b"]
  },
  "action": {
    "type": "show_question",
    "targetQuestionId": "question_tag_followup"
  }
}
```

```json
{
  "id": "logic_not_exists_tags",
  "when": {
    "questionId": "question_tags",
    "operator": "not_exists",
    "optionIds": ["option_none"]
  },
  "action": {
    "type": "show_question",
    "targetQuestionId": "question_continue"
  }
}
```

---

## 14. Answered / not answered

```json
{
  "id": "logic_answered_followup",
  "when": {
    "questionId": "question_contact",
    "operator": "answered"
  },
  "action": {
    "type": "show_question",
    "targetQuestionId": "question_contact_confirm"
  }
}
```

```json
{
  "id": "logic_not_answered_reminder",
  "when": {
    "questionId": "question_contact",
    "operator": "not_answered"
  },
  "action": {
    "type": "show_question",
    "targetQuestionId": "question_contact_reminder"
  }
}
```

---

## 15. Conflict ordering template

When you intentionally rely on conflict priority, place the stronger final intent later.

### Example: final question should be visible

```json
[
  {
    "id": "logic_hide_first",
    "when": { "questionId": "question_gate", "operator": "selected", "optionId": "option_yes" },
    "action": { "type": "hide_question", "targetQuestionId": "question_target" }
  },
  {
    "id": "logic_show_last",
    "when": { "questionId": "question_gate", "operator": "selected", "optionId": "option_yes" },
    "action": { "type": "show_question", "targetQuestionId": "question_target" }
  }
]
```

### Example: final option should be hidden

```json
[
  {
    "id": "logic_show_first",
    "when": { "questionId": "question_gate", "operator": "selected", "optionId": "option_yes" },
    "action": {
      "type": "show_option",
      "targetQuestionId": "question_modes",
      "targetOptionId": "option_advanced"
    }
  },
  {
    "id": "logic_hide_last",
    "when": { "questionId": "question_gate", "operator": "selected", "optionId": "option_yes" },
    "action": {
      "type": "hide_option",
      "targetQuestionId": "question_modes",
      "targetOptionId": "option_advanced"
    }
  }
]
```

---

## 16. Recommended composition patterns

### AI recommendation path
- `show_option`
- `auto_select_option`
- optional `hide_option` for incompatible paths

### Fast-path onboarding
- `jump_to_page`
- `hide_question`
- auto-select the preferred final option

### Qualification screening
- `end_survey`
- all later questions automatically become skipped/nonexistent

### Stateful cleanup
- use `show_question` for conditional questions
- when the condition becomes false, hidden answers are automatically removed from cache and payload
