# 钉钉日报 GitHub Actions 迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 dingtalk-digest 的三个脚本迁移到 GitHub Actions，实现定时自动推送，脱离本地电脑依赖。

**Architecture:** 每个脚本对应一个独立 workflow 文件，Secrets 通过 GitHub 环境变量注入，脚本修改为优先读环境变量、无则读 config.json。

**Tech Stack:** GitHub Actions, Python 3.12（标准库，无额外依赖）

## Global Constraints

- 三个 workflow 文件独立，互不影响
- config.json 不提交到 GitHub，仅本地调试用
- 脚本不依赖任何第三方 Python 包（标准库即可运行）
- 定时使用 UTC 时间，对应北京时间 10:07/18:04/10:30

---

### Task 1: 更新 .gitignore，确保 config.json 不提交

**Files:**
- Modify: `dingtalk-digest/.gitignore`

**Interfaces:**
- Produces: `.gitignore` 中包含 `config.json`

- [ ] **Step 1: 读取现有 .gitignore**

读取 `dingtalk-digest/.gitignore` 内容。

- [ ] **Step 2: 添加 config.json 到 .gitignore**

如果文件中没有 `config.json`，添加一行：
```
config.json
```

```bash
# 在文件末尾追加（如果还没有）
echo "config.json" >> "C:\Users\LD1621\Desktop\7,8,9,10月发运+收货计划\dingtalk-digest\.gitignore"
```

- [ ] **Step 3: 提交**

```bash
git add dingtalk-digest/.gitignore
git commit -m "chore: 排除 config.json 不提交到 GitHub"
```

---

### Task 2: 修改 dingtalk_common.py，支持环境变量

**Files:**
- Modify: `dingtalk-digest/dingtalk_common.py`

**Interfaces:**
- Produces: `load_config()` 优先返回环境变量拼接的字典，无环境变量则读 config.json

- [ ] **Step 1: 读取现有 dingtalk_common.py**

已读取，确认 `load_config()` 函数在第 18-20 行。

- [ ] **Step 2: 替换 load_config 函数**

将现有的 `load_config` 函数替换为支持环境变量的版本：

```python
def load_config(path=CONFIG_PATH):
    # 优先读环境变量（GitHub Secrets 注入），无则读 config.json（本地调试用）
    cfg = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    return {
        "mcp_url": os.environ.get("DINGTALK_MCP_URL") or cfg.get("mcp_url", ""),
        "calendar_mcp_url": os.environ.get("DINGTALK_CALENDAR_MCP_URL") or cfg.get("calendar_mcp_url", ""),
        "table_mcp_url": os.environ.get("DINGTALK_TABLE_MCP_URL") or cfg.get("table_mcp_url", ""),
        "base_id": os.environ.get("DINGTALK_BASE_ID") or cfg.get("base_id", ""),
        "table_id": os.environ.get("DINGTALK_TABLE_ID") or cfg.get("table_id", ""),
        "robot_webhook": os.environ.get("DINGTALK_ROBOT_WEBHOOK") or cfg.get("robot_webhook", ""),
        "robot_secret": os.environ.get("DINGTALK_ROBOT_SECRET") or cfg.get("robot_secret", ""),
    }
```

- [ ] **Step 3: 测试 load_config**

创建临时测试文件 `test_load_config.py`：

```python
import os, json, tempfile
from dingtalk_common import load_config

# 测试1：无环境变量，无 config.json
os.environ.pop("DINGTALK_MCP_URL", None)
cfg = load_config("/nonexistent/path.json")
assert cfg.get("mcp_url") == "", "should be empty string"

# 测试2：无环境变量，有 config.json
with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
    json.dump({"mcp_url": "http://local"}, f)
    tmp = f.name
cfg = load_config(tmp)
assert cfg["mcp_url"] == "http://local"
os.unlink(tmp)

# 测试3：环境变量优先
os.environ["DINGTALK_MCP_URL"] = "http://env"
cfg = load_config(tmp if os.path.exists(tmp) else "/nonexistent/path.json")
assert cfg["mcp_url"] == "http://env"
os.environ.pop("DINGTALK_MCP_URL")

print("All load_config tests passed!")
```

运行：
```bash
cd "C:\Users\LD1621\Desktop\7,8,9,10月发运+收货计划\dingtalk-digest" && python test_load_config.py
```

- [ ] **Step 4: 清理测试文件，提交**

```bash
rm test_load_config.py
git add dingtalk-digest/dingtalk_common.py
git commit -m "feat: load_config 支持环境变量优先，兼容 GitHub Actions"
```

---

### Task 3: 创建三个 workflow 文件

**Files:**
- Create: `dingtalk-digest/.github/workflows/dingtalk-daily-digest.yml`
- Create: `dingtalk-digest/.github/workflows/dingtalk-calendar-briefing.yml`
- Create: `dingtalk-digest/.github/workflows/dingtalk-task-weekly.yml`

**Interfaces:**
- Produces: 三个 workflow 文件，每个可独立触发定时任务

- [ ] **Step 1: 创建 .github/workflows 目录**

```bash
mkdir -p "C:\Users\LD1621\Desktop\7,8,9,10月发运+收货计划\dingtalk-digest\.github\workflows"
```

- [ ] **Step 2: 创建 dingtalk-daily-digest.yml（早报，工作日 10:07 UTC=2:07）**

```yaml
name: 钉钉早报（待办日报）

on:
  schedule:
    # 北京时间 10:07，工作日
    - cron: '7 2 * * 1-5'
  workflow_dispatch:

jobs:
  send-daily-digest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Run daily digest
        env:
          DINGTALK_MCP_URL: ${{ secrets.DINGTALK_MCP_URL }}
          DINGTALK_ROBOT_WEBHOOK: ${{ secrets.DINGTALK_ROBOT_WEBHOOK }}
          DINGTALK_ROBOT_SECRET: ${{ secrets.DINGTALK_ROBOT_SECRET }}
        run: python dingtalk_daily_digest.py
```

- [ ] **Step 3: 创建 dingtalk-calendar-briefing.yml（晚报，工作日 18:04 UTC=10:04）**

```yaml
name: 钉钉晚报（明日行程）

on:
  schedule:
    # 北京时间 18:04，工作日
    - cron: '4 10 * * 1-5'
  workflow_dispatch:

jobs:
  send-calendar-briefing:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Run calendar briefing
        env:
          DINGTALK_CALENDAR_MCP_URL: ${{ secrets.DINGTALK_CALENDAR_MCP_URL }}
          DINGTALK_ROBOT_WEBHOOK: ${{ secrets.DINGTALK_ROBOT_WEBHOOK }}
          DINGTALK_ROBOT_SECRET: ${{ secrets.DINGTALK_ROBOT_SECRET }}
        run: python dingtalk_calendar_briefing.py
```

- [ ] **Step 4: 创建 dingtalk-task-weekly.yml（周报，周一 10:30 UTC=2:30）**

```yaml
name: 钉钉周报（团队任务）

on:
  schedule:
    # 北京时间周一 10:30
    - cron: '30 2 * * 1'
  workflow_dispatch:

jobs:
  send-task-weekly:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Run task weekly
        env:
          DINGTALK_TABLE_MCP_URL: ${{ secrets.DINGTALK_TABLE_MCP_URL }}
          DINGTALK_BASE_ID: ${{ secrets.DINGTALK_BASE_ID }}
          DINGTALK_TABLE_ID: ${{ secrets.DINGTALK_TABLE_ID }}
          DINGTALK_ROBOT_WEBHOOK: ${{ secrets.DINGTALK_ROBOT_WEBHOOK }}
          DINGTALK_ROBOT_SECRET: ${{ secrets.DINGTALK_ROBOT_SECRET }}
        run: python dingtalk_task_weekly.py
```

- [ ] **Step 5: 提交**

```bash
git add dingtalk-digest/.github/
git commit -m "feat: 添加三个 GitHub Actions workflow（早报/晚报/周报）"
```

---

### Task 4: 验证脚本兼容性

**Files:**
- Modify: `dingtalk-digest/dingtalk_daily_digest.py`
- Modify: `dingtalk-digest/dingtalk_calendar_briefing.py`
- Modify: `dingtalk-digest/dingtalk_task_weekly.py`

**Interfaces:**
- Produces: 三个脚本均通过 load_config() 读取配置，无需 config.json 也能运行

- [ ] **Step 1: 确认三个脚本的 load_config 调用方式**

读取三个脚本，确认它们调用 `load_config()` 时传入 `args.config`，无 `--config` 参数时 `args.config` 为 `None`，触发 `load_config()` 使用默认 `CONFIG_PATH`（`config.json`）。

由于 dingtalk_common.py 已改为：无环境变量时读 config.json（存在则读，不存在则返回空字符串），本地调试仍可用 config.json，GitHub Actions 无 config.json 时通过环境变量获取。三个脚本无需修改。

- [ ] **Step 2: dry-run 验证（本地）**

```bash
cd "C:\Users\LD1621\Desktop\7,8,9,10月发运+收货计划\dingtalk-digest" && python dingtalk_daily_digest.py --dry-run 2>&1
cd "C:\Users\LD1621\Desktop\7,8,9,10月发运+收货计划\dingtalk-digest" && python dingtalk_calendar_briefing.py --dry-run 2>&1
cd "C:\Users\LD1621\Desktop\7,8,9,10月发运+收货计划\dingtalk-digest" && python dingtalk_task_weekly.py --dry-run 2>&1
```

确认三个脚本在本地 config.json 存在时仍正常输出预览。

- [ ] **Step 3: 提交（如有变更）**

如三个脚本无需修改，直接跳过。如有微调：
```bash
git add dingtalk-digest/
git commit -m "chore: 验证脚本兼容性（无需代码变更）"
```

---

### Task 5: 部署指南

**Files:**
- Modify: `dingtalk-digest/README.md`

- [ ] **Step 1: 在 README.md 末尾追加 GitHub Actions 部署说明**

在 README.md 末尾添加：

```markdown
---

## GitHub Actions 部署（可选）

将本项目部署到 GitHub Actions，摆脱本地电脑依赖。

### 第一步：创建 GitHub 私有仓库

在 GitHub 创建私有仓库（如 `dingtalk-digest`），将项目 push 上去。

> **注意**：`config.json` 已通过 `.gitignore` 排除，不会提交到 GitHub。

### 第二步：配置 Secrets

在仓库页面 → Settings → Secrets and variables → Actions，添加以下 7 个 Secret：

| Secret 名 | 来源 |
|-----------|------|
| `DINGTALK_MCP_URL` | 来自 config.json 的 `mcp_url` |
| `DINGTALK_CALENDAR_MCP_URL` | 来自 config.json 的 `calendar_mcp_url` |
| `DINGTALK_TABLE_MCP_URL` | 来自 config.json 的 `table_mcp_url` |
| `DINGTALK_BASE_ID` | 来自 config.json 的 `base_id` |
| `DINGTALK_TABLE_ID` | 来自 config.json 的 `table_id` |
| `DINGTALK_ROBOT_WEBHOOK` | 来自 config.json 的 `robot_webhook` |
| `DINGTALK_ROBOT_SECRET` | 来自 config.json 的 `robot_secret` |

### 第三步：验证

在 GitHub 仓库 → Actions 页面，手动触发任一 workflow，确认消息正常发送到钉钉群。

### 定时说明

| Workflow | 北京时间 | 触发条件 |
|----------|----------|----------|
| 钉钉早报 | 工作日 10:07 | 自动 |
| 钉钉晚报 | 工作日 18:04 | 自动 |
| 钉钉周报 | 周一 10:30 | 自动 |

也可以手动触发（workflow_dispatch）：仓库 → Actions → 选择 workflow → Run workflow。
```

- [ ] **Step 2: 提交**

```bash
git add dingtalk-digest/README.md
git commit -m "docs: 添加 GitHub Actions 部署说明"
```

---

## 自检清单

- [ ] `.github/workflows/` 下有 3 个 yml 文件
- [ ] `dingtalk_common.py` 的 `load_config` 支持环境变量
- [ ] `config.json` 在 `.gitignore` 中
- [ ] README.md 包含 GitHub Actions 部署步骤
- [ ] 三个 workflow 均有 `workflow_dispatch` 方便手动触发
- [ ] 所有变更已提交
