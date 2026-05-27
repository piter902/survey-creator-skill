# survey-creator-skill real-world evals

真实业务回归集，用来验证 `survey-creator-skill` 能否把常见业务 prompt 稳定落成可投放 HTML。

每个 case 包含：

- `prompt.md`：用户真实需求
- `schema.json`：根据 prompt 产出的 golden schema
- `expected.json`：业务验收断言，例如题型覆盖、最少题数、关键 id

运行：

```bash
python3 <survey-creator-root>/evals/real-world/run_real_world_evals.py
```

输出：

- `outputs/<case-id>/*.html`
- `outputs/<case-id>/*.payload.json`
- `outputs/<case-id>/*.pipeline-report.json`
- `outputs/real-world-eval-report.json`

通过标准：

- schema / html runtime / desktop+mobile E2E / desktop+mobile interaction E2E / accessibility / payload / payloadAgainstSchema 全部通过
- `releaseDecision.shipReady === true`
- case 自身业务断言全部通过

这些 eval 不替代人工业务判断，但可以防止 skill 改动后破坏真实问卷生成能力。
