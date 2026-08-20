# Declarative Case Runtime 离线验证证据

验证日期：2026-08-20

## Framework test suite

```text
180 passed
```

本次验证在包含真实 `.git` 元数据的原始仓库副本上执行，Repository Hygiene 的 Git index 检查也实际运行并通过。

## Mock Demo

```text
smoke       2 passed, 4 deselected
core        2 passed, 4 deselected
regression  2 passed, 4 deselected
```

Demo 已删除三个业务 Python wrapper，六条普通 Case 由 `testcases/test_yaml_cases.py` 唯一 Generic Runtime 收集。

## Shortlink collection

```text
Total       18
Smoke        6
Core         6
Regression   6
```

结构：

```text
16 declarative YAML Cases
2 Python lifecycle Workflows
```

两条 Workflow 都是 Recycle Storage 多状态 Regression；其余普通 Case 不再维护项目顶层 `test_*.py` wrapper。

## Compile

```text
python -m compileall -q ai core db utils testcases tests run.py conftest.py
PASS
```

## Secret / Release scan

```text
SECRET_SCAN=PASS
```

检查包括：

- `config/ai.local.yaml` 可以本机存在，但必须被 `.gitignore` 且不得被 Git 跟踪；发布包会排除它；
- `.env` 不存在于交付树；
- `config/env.*.private.yaml` 不存在于交付树；
- 公共 config 中 secret-like 字段为占位/空值；
- 未发现常见 OpenAI-style Key、JWT、AWS Access Key 形态。

## 真实 SUT 边界

Shortlink 旧执行模型已经有真实 Smoke/Core/Regression 通过证据，但本轮改变了 collection/context/workflow 执行模型，因此不能沿用旧证据冒充新版本通过。

本轮只确认 `shortlink-local` 三层 `--collect-only` 均为 `6/18`；新的 Declarative Runtime 仍需用户 Windows 真实 SUT 重新执行 Smoke/Core/Regression 验收。
