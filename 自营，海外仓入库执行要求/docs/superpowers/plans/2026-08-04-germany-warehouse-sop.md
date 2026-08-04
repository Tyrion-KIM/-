# 德国海外仓执行SOP — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建德国自营海外仓执行SOP HTML页面（v1测试版），8个作业节点 × 双角色视角，支持库内操作/中台调度切换和PDF导出。

**Architecture:** 单文件纯静态HTML，CSS Grid双列布局（固定导航+滚动内容区），JS处理标签切换/节点折叠/打印适配，无框架依赖。

**Tech Stack:** HTML5 + CSS3 + Vanilla JS (ES6)

## Global Constraints

- 纯静态HTML，零外部依赖
- 色系：主色 `#2563eb`，沿用物流成本模型品牌色
- 最小作业单元：托盘级别（非箱级/件级）
- 中等颗粒度：写清流程要求/责任方/检查标准，不逐按钮截图
- 文件名：`德国仓执行SOP_v1.html`
- 入库起点：货物到仓门口，不覆盖港口→仓库段
- 支持 Ctrl+P 打印为PDF（自动全部展开+隐藏UI）

## File Structure

| 文件 | 职责 |
|---|---|
| `德国仓执行SOP_v1.html` | 唯一交付物：结构+样式+脚本+全部SOP内容 |

单文件设计原因：无需构建工具，离线可用，一份文件即可在浏览器中完整查阅和打印。

---

### Task 1: HTML 骨架 — 结构 + 样式 + 交互逻辑

**Files:**
- Create: `德国仓执行SOP_v1.html`

**Interfaces:**
- Produces:
  - HTML结构：`<nav id="node-nav">` 导航区、`<main id="content">` 内容区
  - CSS类：`.role-tab` 角色标签、`.node-panel` 节点面板、`.field-*` 字段样式
  - JS函数：`switchRole(role)` 切换角色、`openNode(index)` 展开节点、`initPrintMode()` 打印适配
  - 数据属性：`data-role="warehouse|dispatch"` 标记角色内容块

- [ ] **Step 1: 创建HTML文件基础结构**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>德国海外仓执行SOP v1</title>
  <style>/* CSS goes here */</style>
</head>
<body>
  <header id="header">...</header>
  <div id="app">
    <nav id="node-nav">...</nav>
    <main id="content">...</main>
  </div>
  <footer id="footer">...</footer>
  <script>/* JS goes here */</script>
</body>
</html>
```

- [ ] **Step 2: 写Header区域 — 标题栏 + 角色切换标签**

```html
<header id="header">
  <div class="header-top">
    <h1>🏭 德国海外仓执行SOP</h1>
    <span class="badge">自营仓 · 物流执行标准</span>
  </div>
  <div class="role-tabs">
    <button class="role-tab active" data-role="warehouse" onclick="switchRole('warehouse')">
      📦 库内操作
    </button>
    <button class="role-tab" data-role="dispatch" onclick="switchRole('dispatch')">
      🖥️ 中台调度
    </button>
  </div>
</header>
```

- [ ] **Step 3: 写左侧导航栏结构**

```html
<nav id="node-nav">
  <ul class="nav-list">
    <li><a href="#node-1" class="nav-item active" onclick="openNode(1)">1. 车辆到仓 & 核实</a></li>
    <li><a href="#node-2" class="nav-item" onclick="openNode(2)">2. 卸货 & 验收</a></li>
    <li><a href="#node-3" class="nav-item" onclick="openNode(3)">3. 上架</a></li>
    <li><a href="#node-4" class="nav-item" onclick="openNode(4)">4. 库内存储</a></li>
    <li><a href="#node-5" class="nav-item" onclick="openNode(5)">5. 拣货下架</a></li>
    <li><a href="#node-6" class="nav-item" onclick="openNode(6)">6. 打包</a></li>
    <li><a href="#node-7" class="nav-item" onclick="openNode(7)">7. 出库装车 & 车辆核实</a></li>
    <li><a href="#node-8" class="nav-item" onclick="openNode(8)">8. 库内设备 & 场地调度</a></li>
  </ul>
  <hr>
  <ul class="nav-list nav-appendix">
    <li><a href="#appendix-exception" class="nav-item" onclick="openAppendix('exception')">📎 异常处理汇总</a></li>
    <li><a href="#appendix-form" class="nav-item" onclick="openAppendix('form')">📎 关联表单</a></li>
  </ul>
</nav>
```

- [ ] **Step 4: 写内容区面板结构（一个节点示例）**

```html
<main id="content">
  <!-- Node 1: 车辆到仓 & 核实 -->
  <section id="node-1" class="node-panel active">
    <h2 class="node-title">1. 车辆到仓 & 核实</h2>

    <!-- 库内操作内容 -->
    <div class="role-content" data-role="warehouse">
      <div class="field">
        <h3 class="field-label">目的</h3>
        <p class="field-body"><!-- 填充内容 --></p>
      </div>
      <div class="field">
        <h3 class="field-label">前置条件</h3>
        <ul class="field-body"><!-- 填充内容 --></ul>
      </div>
      <div class="field">
        <h3 class="field-label">操作步骤</h3>
        <ol class="field-body steps"><!-- 填充内容 --></ol>
      </div>
      <div class="field">
        <h3 class="field-label">检查标准</h3>
        <ul class="field-body checklist"><!-- 填充内容 --></ul>
      </div>
      <div class="field">
        <h3 class="field-label">交接 / 触发下一节点</h3>
        <p class="field-body"><!-- 填充内容 --></p>
      </div>
      <div class="field">
        <h3 class="field-label">异常场景 & 处理</h3>
        <table class="field-body exception-table"><!-- 填充内容 --></table>
      </div>
    </div>

    <!-- 中台调度内容 -->
    <div class="role-content" data-role="dispatch" style="display:none">
      <!-- 相同6字段结构，内容不同 -->
    </div>
  </section>

  <!-- Node 2-8 同理，使用相同section结构 -->
</main>
```

- [ ] **Step 5: 写Footer — 版本信息 + 修订记录表**

```html
<footer id="footer">
  <div class="footer-info">
    <p>德国海外仓执行SOP · v1 (测试版) · 2026-08-04</p>
  </div>
  <details class="revision-history">
    <summary>📋 修订记录</summary>
    <table>
      <thead>
        <tr><th>版本</th><th>日期</th><th>修订内容</th><th>变更者</th></tr>
      </thead>
      <tbody>
        <tr><td>A1</td><td>2026-08-04</td><td>初版作成 — 8节点双角色框架</td><td>—</td></tr>
      </tbody>
    </table>
  </details>
</footer>
```

- [ ] **Step 6: 写CSS — 全局样式 + 布局**

```css
:root {
  --primary: #2563eb;
  --primary-light: #eff6ff;
  --gray-50: #f9fafb;
  --gray-100: #f3f4f6;
  --gray-200: #e5e7eb;
  --gray-600: #4b5563;
  --gray-800: #1f2937;
  --radius: 8px;
  --shadow: 0 1px 3px rgba(0,0,0,0.1);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  color: var(--gray-800); line-height: 1.6; background: var(--gray-50);
  display: flex; flex-direction: column; min-height: 100vh;
}
```

- [ ] **Step 7: 写CSS — Header + 角色标签样式**

```css
#header {
  background: white; border-bottom: 1px solid var(--gray-200);
  padding: 16px 24px; position: sticky; top: 0; z-index: 100;
}
.header-top { display: flex; align-items: baseline; gap: 12px; margin-bottom: 12px; }
.header-top h1 { font-size: 20px; font-weight: 700; color: var(--gray-800); }
.badge { font-size: 12px; color: var(--gray-600); background: var(--gray-100); padding: 2px 8px; border-radius: 12px; }
.role-tabs { display: flex; gap: 8px; }
.role-tab {
  padding: 8px 20px; border: 1px solid var(--gray-200); border-radius: var(--radius);
  background: white; cursor: pointer; font-size: 14px; font-weight: 500;
  transition: all 0.15s;
}
.role-tab.active { background: var(--primary); color: white; border-color: var(--primary); }
.role-tab:hover:not(.active) { background: var(--primary-light); }
```

- [ ] **Step 8: 写CSS — 主布局 (Grid)**

```css
#app {
  display: grid; grid-template-columns: 240px 1fr; flex: 1; overflow: hidden;
}
```

- [ ] **Step 9: 写CSS — 左侧导航样式**

```css
#node-nav {
  background: white; border-right: 1px solid var(--gray-200);
  padding: 16px 0; overflow-y: auto; position: sticky; top: 0; height: calc(100vh - 120px);
}
.nav-list { list-style: none; }
.nav-item {
  display: block; padding: 10px 24px; font-size: 14px; color: var(--gray-600);
  text-decoration: none; border-left: 3px solid transparent; transition: all 0.15s;
}
.nav-item:hover { background: var(--primary-light); color: var(--primary); }
.nav-item.active { background: var(--primary-light); color: var(--primary); border-left-color: var(--primary); font-weight: 600; }
.nav-appendix .nav-item { color: var(--gray-600); font-size: 13px; }
#node-nav hr { margin: 8px 16px; border: none; border-top: 1px solid var(--gray-200); }
```

- [ ] **Step 10: 写CSS — 内容区 + 节点面板样式**

```css
#content { padding: 24px 32px; overflow-y: auto; height: calc(100vh - 120px); }
.node-panel { display: none; }
.node-panel.active { display: block; }
.node-title { font-size: 22px; font-weight: 700; margin-bottom: 24px; padding-bottom: 12px; border-bottom: 2px solid var(--primary); color: var(--gray-800); }
.field { background: white; border-radius: var(--radius); box-shadow: var(--shadow); padding: 16px 20px; margin-bottom: 16px; }
.field-label {
  font-size: 13px; font-weight: 600; color: var(--primary); text-transform: uppercase;
  letter-spacing: 0.5px; margin-bottom: 8px;
}
.field-body { font-size: 14px; color: var(--gray-600); }
.field-body ul, .field-body ol { padding-left: 20px; }
.field-body li { margin-bottom: 6px; }
.steps .step-executor { font-size: 12px; color: var(--gray-600); background: var(--gray-100); padding: 1px 6px; border-radius: 4px; margin-left: 6px; }
.checklist li::marker { color: var(--primary); }
```

- [ ] **Step 11: 写CSS — 异常表格样式**

```css
.exception-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.exception-table th { background: var(--gray-100); padding: 8px 12px; text-align: left; font-weight: 600; }
.exception-table td { padding: 8px 12px; border-top: 1px solid var(--gray-200); }
.exception-table .escalate { color: #ef4444; font-weight: 600; }
```

- [ ] **Step 12: 写CSS — Footer样式**

```css
#footer {
  background: white; border-top: 1px solid var(--gray-200); padding: 16px 24px;
  font-size: 12px; color: var(--gray-600);
}
.footer-info { margin-bottom: 12px; }
.revision-history summary { cursor: pointer; font-weight: 600; margin-bottom: 8px; }
.revision-history table { width: 100%; border-collapse: collapse; font-size: 12px; }
.revision-history th { background: var(--gray-100); padding: 6px 10px; text-align: left; }
.revision-history td { padding: 6px 10px; border-top: 1px solid var(--gray-200); }
```

- [ ] **Step 13: 写CSS — 打印样式 (@media print)**

```css
@media print {
  #header .role-tabs, #node-nav { display: none !important; }
  #header { position: static; }
  #app { display: block; }
  #content { height: auto; overflow: visible; padding: 0; }
  .node-panel { display: block !important; page-break-before: always; }
  .node-panel:first-of-type { page-break-before: avoid; }
  .node-title { font-size: 18px; }
  .field { box-shadow: none; border: 1px solid var(--gray-200); page-break-inside: avoid; }
  body { background: white; }
  .role-content[data-role="dispatch"] { display: block !important; }
}
```

- [ ] **Step 14: 写JavaScript — 角色切换 + 节点展开 + 打印适配**

```javascript
let currentRole = 'warehouse';
let currentNode = 1;

function switchRole(role) {
  currentRole = role;
  document.querySelectorAll('.role-tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.role === role);
  });
  document.querySelectorAll('.role-content').forEach(el => {
    el.style.display = el.dataset.role === role ? 'block' : 'none';
  });
}

function openNode(index) {
  currentNode = index;
  document.querySelectorAll('.node-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const panel = document.getElementById('node-' + index);
  if (panel) panel.classList.add('active');
  const navItem = document.querySelector('#node-nav .nav-item[href="#node-' + index + '"]');
  if (navItem) navItem.classList.add('active');
}

function openAppendix(type) {
  document.querySelectorAll('.node-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const panel = document.getElementById('appendix-' + type);
  if (panel) panel.classList.add('active');
  const navItem = document.querySelector('#node-nav .nav-item[href="#appendix-' + type + '"]');
  if (navItem) navItem.classList.add('active');
}

window.addEventListener('beforeprint', function() {
  document.querySelectorAll('.node-panel').forEach(p => p.classList.add('active'));
  document.querySelectorAll('.role-content').forEach(el => {
    el.style.display = 'block';
  });
});

window.addEventListener('afterprint', function() {
  document.querySelectorAll('.node-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.role-content').forEach(el => {
    el.style.display = el.dataset.role === currentRole ? 'block' : 'none';
  });
  openNode(currentNode);
});
```

- [ ] **Step 15: 在浏览器打开验证骨架**

在浏览器打开 `德国仓执行SOP_v1.html`，验证：
- 页面渲染正常，无CSS/JS报错
- 角色标签点击切换，库内→中台内容区显示/隐藏
- 左侧导航点击，内容区对应节点展开/折叠
- Ctrl+P 打印预览：全部节点展开 + 两种角色内容都显示 + 导航和标签隐藏

- [ ] **Step 16: Commit**

```bash
git add 德国仓执行SOP_v1.html
git commit -m "feat: 德国仓执行SOP骨架 — 8节点双角色框架+样式+交互"
```

---

### Task 2: SOP内容填充 — 8个节点 × 双角色

**Files:**
- Modify: `德国仓执行SOP_v1.html` — 填充所有 `<!-- 填充内容 -->` 占位符

**Interfaces:**
- Consumes: Task 1 的HTML结构（`.node-panel`、`.role-content`、`.field` 容器）
- Produces: 完整的8节点库内+中台SOP文本内容

由于内容量大（8节点 × 2角色 × 6字段 = 96个内容块），按节点分步填充。每个节点一个commit，便于追溯和回滚。

**内容撰写原则（来自spec）：**
- 中等颗粒度：写清流程要求、责任方、检查标准，不逐按钮描述
- 量化优先：检查标准能用数字就不用描述性语言
- 托盘级别：所有操作围绕托盘，不涉及箱级/件级细节
- 入库起点：货物到仓门口，不覆盖港口→仓库段运输
- 出库端：仓库做车辆核实确认，不负责车辆调度（中台统一指派）

- [ ] **Step 1: 填充节点1 — 车辆到仓 & 核实**

写入以下内容的HTML（两个角色各6字段）：

**库内操作 (data-role="warehouse")：**

- 目的：确保到仓车辆信息准确核实，引导车辆停靠正确码头，完成到仓登记
- 前置条件：中台已推送当日到仓车辆清单（含车牌号、预计到仓时间ETA、货物类型）
- 操作步骤：
  1. 接收中台下发的当日车辆到达清单 → 确认码头可用状态
  2. 车辆到达时，核对车牌号与清单是否一致 → 记录实际到仓时间
  3. 检查车辆外观：封条是否完好、箱体有无破损 → 拍照留档
  4. 指引车辆停靠指定卸货码头
  5. 在系统中录入车辆到达信息（车牌号、到仓时间、码头号）
- 检查标准：
  - 车牌号与清单匹配率 100%
  - 实际到仓时间与ETA偏差记录率 100%
  - 封条/箱体异常拍照留档率 100%
  - 车辆从到仓到停靠码头 ≤ 15分钟
- 交接/触发下一节点：车辆停靠完成 + 系统录入完成 → 通知卸货组开始卸货
- 异常场景 & 处理：
  - 车辆信息与清单不匹配 → 联系中台确认，未确认前不予停靠
  - 封条破损/箱体异常 → 拍照留档，签收时标注异常，通知中台
  - 车辆迟到超过2小时 → 通知中台重新协调码头资源

**中台调度 (data-role="dispatch")：**

- 目的：提前下发出库/入库车辆指派信息，确保仓库有准备时间，异常时及时改派
- 前置条件：已收到出库计划 / 供应商发货通知
- 操作步骤：
  1. 根据入库计划或出库需求，指派运输车辆 → 生成车辆到达清单
  2. 将车辆到达清单（含车牌号、司机联系方式、ETA、货物类型）推送至仓库现场
  3. 跟踪车辆GPS/司机反馈的ETA，如有偏差超过30分钟，更新ETA并通知仓库
  4. 仓库反馈车辆异常时，评估是否需要改派 → 如需改派，30分钟内给出替代方案
- 检查标准：
  - 车辆清单在下发后1小时内推送至仓库
  - ETA偏差超30分钟时，通知率 100%
  - 异常改派响应 ≤ 30分钟
- 交接/触发下一节点：车辆到仓确认后 → 进入卸货验收监控状态
- 异常场景 & 处理：
  - 司机/车辆临时无法到达 → 立即通知仓库释放码头，同时启动改派
  - 车辆严重迟到影响当日计划 → 与仓库协调是否调整卸货优先级或延至次日

- [ ] **Step 2: 填充节点2 — 卸货 & 验收**

**库内操作：**
- 目的：安全高效完成卸货，准确清点托盘数量，完成签收确认
- 前置条件：车辆已停靠指定码头、卸货设备（叉车）就位、签收单据准备就绪
- 操作步骤：
  1. 叉车操作员就位，确认卸货区域无人员/障碍物
  2. 逐托盘卸货：检查每个托盘外观完整性（缠绕膜是否完好、托盘有无破损倾斜）
  3. 清点托盘总数，与送货单/系统数据核对
  4. 在系统中完成签收确认（托盘数量、到仓时间、车牌号）
  5. 将卸货完成的托盘移至待上架暂存区
- 检查标准：
  - 托盘数量与单据一致率 100%（差异需当场确认并记录）
  - 单个托盘卸货耗时 ≤ 3分钟
  - 托盘外观破损记录率 100%
  - 卸货区域作业完毕后即时清理
- 交接/触发下一节点：签收确认完成 + 托盘移至暂存区 → 触发上架任务
- 异常场景 & 处理：
  - 托盘数量与单据不符 → 当场与司机确认，签收单备注差异，拍照留档，通知中台
  - 托盘破损/倾斜 → 单独存放于异常区，拍照留档，暂不签收该托盘，通知中台对接供应商
  - 送货单信息缺失 → 拒收，联系中台补全信息后重新安排

**中台调度：**
- 目的：实时掌握验收数据，发现差异第一时间与供应商/物流商对接处理
- 前置条件：仓库签收数据同步至系统
- 操作步骤：
  1. 监控签收数据：托盘数量、签收时间、异常标记
  2. 发现数量差异/破损 → 15分钟内联系供应商或物流商确认
  3. 将差异处理结果反馈仓库 → 更新系统数据
  4. 对反复出现差异的供应商/物流商，记录并纳入考核
- 检查标准：
  - 差异响应 ≤ 15分钟
  - 差异关闭（确认处理方案）≤ 2小时
  - 供应商/物流商异常记录完整率 100%
- 交接/触发下一节点：验收数据确认无误 → 进入上架进度跟踪
- 异常场景 & 处理：
  - 供应商不认可差异 → 提供签收照片及司机签字记录作为凭据
  - 大批量差异（≥5托盘）→ 升级至物流主管，协调供应商现场确认

- [ ] **Step 3: 填充节点3 — 上架**

**库内操作：**
- 目的：将验收完成的托盘按库位策略上架，绑定库位信息，确保库存数据准确
- 前置条件：托盘已完成签收、系统已分配库位（或按现场规则自选库位）
- 操作步骤：
  1. 根据系统分配的库位（或现场上架规则），规划上架路径
  2. 叉车搬运托盘至指定库位
  3. 使用PDA/扫码设备扫描托盘标签 + 库位标签 → 系统绑定
  4. 确认上架完成：检查托盘摆放稳定性，托盘不得超出库位线
  5. 系统更新上架状态为"已完成"
- 检查标准：
  - 库位绑定准确率 100%
  - 上架完成到系统更新 ≤ 5分钟
  - 托盘摆放合规率 100%（不超线、不超高、堆码下大上小）
- 交接/触发下一节点：上架完成 + 系统状态更新 → 库存可售/可用
- 异常场景 & 处理：
  - 系统分配库位已被占用 → 记录并反馈中台更新库位策略，暂放临近空库位
  - 托盘标签无法识别 → 重新打印标签粘贴，确认库位绑定无误后方可离开
  - 库位空间不足 → 报告现场主管，协调临时存放区域

**中台调度：**
- 目的：跟踪上架进度，确保库位策略合理，及时调整避免库位浪费
- 前置条件：签收完成数据已确认
- 操作步骤：
  1. 监控上架完成率（按日/按批次），上架任务下发后2小时内应有完成反馈
  2. 定期审核库位利用率，低于70%时调整库位策略
  3. 协调上架优先级：急货优先、同SKU集中存放
- 检查标准：
  - 当日到货上架完成率 ≥ 95%
  - 库位利用率 ≥ 70%
  - 急货上架优先执行率 100%
- 交接/触发下一节点：上架完成确认 → 库存数据进入正常监控周期
- 异常场景 & 处理：
  - 上架进度滞后（超2小时未完结）→ 联系现场主管了解原因，调整人力或优先级
  - 系统库位数据与实物的偏差 → 发起盘点指令

- [ ] **Step 4: 填充节点4 — 库内存储**

**库内操作：**
- 目的：保证库内托盘存储安全、有序，库存数据与实物一致
- 前置条件：托盘已上架完成，库位信息正确
- 操作步骤：
  1. 日常库位整理：检查托盘摆放合规（不超线、不超高、堆码稳固），移位调整
  2. 按中台下发的盘点计划执行盘点：逐库位核对托盘数量+SKU
  3. 盘点结果录入系统，差异标注原因
  4. 托盘移位时同步更新系统库位
- 检查标准：
  - 月度盘点准确率 ≥ 99%
  - 库位合规（不超线/超高）巡检合格率 100%
  - 移位后库位更新率 100%
- 交接/触发下一节点：库存数据准确 → 支持拣货任务正常下发
- 异常场景 & 处理：
  - 盘点差异 → 二次复盘确认，如确为差异则标记盘盈/盘亏，上报中台
  - 托盘损坏/倾斜 → 移至异常区，登记损坏情况，上报中台
  - 库位标签脱落 → 补打标签，确认库位绑定无误

**中台调度：**
- 目的：通过数据监控确保库存准确性，周期性下发盘点计划
- 前置条件：系统库存数据可用
- 操作步骤：
  1. 每月初下发盘点计划（全盘或抽盘），明确盘点范围和截止时间
  2. 监控盘点进度和差异率，差异率超1%时要求复盘
  3. 盘点结果审核确认，生成盘点报告
  4. 监控长期滞留库存（超90天未动托盘），定期输出滞销预警
- 检查标准：
  - 月度盘点计划下发率 100%
  - 盘点差异关闭率 100%（确认差异原因并处理）
  - 滞销库存预警月报推送率 100%
- 交接/触发下一节点：库存数据健康 → 支持拣货/出库计划正常执行
- 异常场景 & 处理：
  - 盘点差异率异常升高（超3%）→ 升级至物流主管，启动专项核查
  - 系统库存与WMS不一致 → 技术排查数据同步问题

- [ ] **Step 5: 填充节点5 — 拣货下架**

**库内操作：**
- 目的：按拣货单准确下架指定托盘，移至出库暂存区
- 前置条件：收到拣货任务单（中台下发）、叉车可用
- 操作步骤：
  1. 接收拣货任务，确认拣货单信息（SKU、库位、托盘数量、优先级）
  2. 按拣货单指引前往库位，核对托盘标签与拣货单是否一致
  3. 叉车将目标托盘下架
  4. 将下架托盘移至出库暂存区指定位置
  5. PDA扫描确认下架完成，系统更新状态
- 检查标准：
  - 拣货准确率 100%（托盘+数量+SKU一致）
  - 单托盘拣货耗时 ≤ 5分钟（含下架+运输至暂存区）
  - 下架后库位状态更新率 100%
- 交接/触发下一节点：拣货下架完成 + 托盘在暂存区就位 → 触发打包工序
- 异常场景 & 处理：
  - 库位实物与拣货单不一致 → 暂停拣货，核实库存数据，反馈中台
  - 目标托盘被其他货物阻挡 → 协调叉车移位，评估是否调整拣货顺序
  - 托盘标签无法识别 → 人工核对SKU+数量确认，通知中台补打标签

**中台调度：**
- 目的：合理下发拣货任务，按出库优先级调度，确保按时备货
- 前置条件：出库计划已确认
- 操作步骤：
  1. 根据出库计划生成拣货任务，标注优先级（正常/加急）
  2. 下发拣货任务至仓库现场
  3. 跟踪拣货完成进度，确保在装车前的规定时间内完成
  4. 根据实际情况动态调整拣货优先级
- 检查标准：
  - 拣货任务下发及时率 100%（不晚于装车计划前3小时）
  - 加急单拣货完成率 100%
  - 任务下发到拣货完成平均时长跟踪（目标：≤ 2小时/批次）
- 交接/触发下一节点：拣货完成确认 → 进入出库装车协调阶段
- 异常场景 & 处理：
  - 拣货进度滞后（影响装车计划）→ 联系现场主管协调加派人手
  - 库存不足无法满足拣货 → 启动缺货流程，通知相关部门

- [ ] **Step 6: 填充节点6 — 打包**

**库内操作：**
- 目的：对拣货完成的托盘进行加固打包、粘贴出库标签，确保托盘在运输途中完好
- 前置条件：托盘已拣货下架至暂存区
- 操作步骤：
  1. 检查托盘货物稳定性：堆码是否整齐、有无松动倾斜
  2. 使用缠绕膜/打包带对托盘进行加固包装
  3. 粘贴出库标签（含目的地、SKU、托盘编号、件数）
  4. 系统更新托盘状态为"已打包，待出库"
  5. 将打包完成的托盘移至出库待装区
- 检查标准：
  - 托盘打包牢固，手动摇晃无明显松动
  - 出库标签粘贴率 100%，标签信息与出库单一致
  - 打包完成到系统更新 ≤ 5分钟
- 交接/触发下一节点：打包完成 + 移至出库待装区 → 等待车辆到仓装车
- 异常场景 & 处理：
  - 托盘货物松散/倾斜 → 重新码垛后打包，记录原因
  - 出库标签信息错误 → 废弃错误标签，重新打印正确的标签
  - 打包材料（缠绕膜/打包带）不足 → 提前预警库存，最低库存量满足3天用量

**中台调度：** 此节点中台不直接参与操作，通过系统监控出库状态更新。

- [ ] **Step 7: 填充节点7 — 出库装车 & 车辆核实**

**库内操作：**
- 目的：安全高效完成装车，核实提货车辆信息，确保出库准确
- 前置条件：打包完成、托盘在待装区、提货车辆已到仓
- 操作步骤：
  1. 核对提货车辆信息（车牌号、司机身份）与中台下发的出库车辆清单一致
  2. 确认车辆停靠装货码头
  3. 按装车单顺序逐托盘装车 → 装车时核对托盘标签与装车单
  4. 装车完成后与司机共同确认装载托盘数量，双方签字确认
  5. 系统完成出库确认，车辆放行
- 检查标准：
  - 提货车辆信息核实率 100%（未经核实的车辆不予装车）
  - 装车准确率 100%（出库托盘与装车单一致）
  - 单车装车耗时 ≤ 30分钟（标准柜）
- 交接/触发下一节点：出库确认完成 → 系统库存扣减 → 物流中台确认放行
- 异常场景 & 处理：
  - 提货车辆信息与清单不匹配 → 不予装车，联系中台确认
  - 装车时发现托盘数量/标签异常 → 暂停装车，核对确认后再继续
  - 装车过程中货物损坏 → 拍照留档，更换托盘，记录原因

**中台调度：**
- 目的：确保提货车辆按时到达，传递准确的司机/车辆信息给仓库，完成放行确认
- 前置条件：出库计划已生成
- 操作步骤：
  1. 根据出库计划指派运输车辆，生成出库车辆清单
  2. 将出库车辆清单（车牌号、司机姓名+联系方式、计划到仓时间）推送至仓库
  3. 跟踪提货车辆ETA，偏差超30分钟通知仓库调整装车计划
  4. 仓库完成装车确认后，做最终放行确认
- 检查标准：
  - 出库车辆清单在装车时间前2小时推送至仓库
  - 司机信息（车牌号+联系方式）准确率 100%
  - 放行确认及时率 100%
- 交接/触发下一节点：出库放行 → 运输在途跟踪
- 异常场景 & 处理：
  - 提货车辆迟到→ 与承运商确认原因，协调仓库是否延后装车或改派
  - 司机信息错误 → 5分钟内推送更正信息给仓库
  - 临时更换车辆 → 立即通知仓库更新核对信息

- [ ] **Step 8: 填充节点8 — 库内设备 & 场地调度**

**库内操作：**
- 目的：合理调度叉车和码头资源，维护库内动线秩序，确保作业安全高效
- 前置条件：当日作业计划已明确（入库/出库量、车辆台次）
- 操作步骤：
  1. 每日开工前确认叉车可用状态（电量/油量、外观检查）
  2. 根据当日入库/出库计划分配码头：入库优先使用1-2号码头，出库使用3-4号
  3. 作业高峰时段调配叉车资源，确保入库/出库不互相阻塞
  4. 维护库内主通道畅通，禁止托盘占道存放
  5. 每日收工检查：叉车归位充电/停放、码头清理、通道无障碍
- 检查标准：
  - 叉车可用率 ≥ 98%（每日开工检查通过）
  - 码头分配无冲突（同一码头不同时安排入+出）
  - 主通道堵塞次数 = 0
  - 每日收工检查完成率 100%
- 交接/触发下一节点：贯穿所有节点的日常保障工作
- 异常场景 & 处理：
  - 叉车故障 → 启动备用叉车，故障叉车报修并贴禁用标签
  - 码头不足（多车同时到达）→ 按中台优先级排序，其余车辆在等候区排队
  - 通道被占 → 立即清理并追溯责任人

**中台调度：** 此节点中台不直接参与操作，通过当日车辆计划间接影响码头使用。

- [ ] **Step 9: 填充附录 — 异常处理汇总 + 关联表单**

```html
<section id="appendix-exception" class="node-panel">
  <h2 class="node-title">📎 异常处理汇总</h2>
  <div class="field">
    <h3 class="field-label">异常升级路径</h3>
    <table class="exception-table">
      <thead>
        <tr><th>级别</th><th>异常描述</th><th>现场处理</th><th>中台处理</th><th>升级条件</th></tr>
      </thead>
      <tbody>
        <tr><td>L1</td><td>单托盘标签/外观问题</td><td>拍照留档，移至异常区</td><td>-</td><td>-</td></tr>
        <tr><td>L2</td><td>数量差异/信息不匹配</td><td>保留现场，暂不签收</td><td>15分钟内联系物流商</td><td>2小时未解决→L3</td></tr>
        <tr><td>L3</td><td>批量差异(≥5托盘)/车辆异常</td><td>停止作业，保护现场</td><td>1小时内协调现场确认</td><td>当日未解决→L4</td></tr>
        <tr><td>L4</td><td>系统性异常/安全事件</td><td>启动应急预案</td><td>升级至物流主管+仓库负责人</td><td>实时通知</td></tr>
      </tbody>
    </table>
  </div>
</section>

<section id="appendix-form" class="node-panel">
  <h2 class="node-title">📎 关联表单</h2>
  <div class="field">
    <ul>
      <li>车辆到达清单（中台下发给仓库）</li>
      <li>签收确认单（仓库操作留底+司机签字）</li>
      <li>出库车辆清单（中台下发给仓库）</li>
      <li>装车确认单（仓库+司机双方签字）</li>
      <li>异常记录表（含照片）</li>
      <li>盘点报告（中台生成+审核）</li>
    </ul>
  </div>
</section>
```

- [ ] **Step 10: Commit**

```bash
git add 德国仓执行SOP_v1.html
git commit -m "feat: SOP内容填充 — 8节点双角色完整内容+附录"
```

---

### Task 3: 定稿检查 — 内容复核 + 打印验证 + 版本信息

**Files:**
- Modify: `德国仓执行SOP_v1.html`

- [ ] **Step 1: 内容自检**

逐节点朗读检查，确认以下标准：
- 每个节点6字段全部填充完整，无占位符残留
- 量化指标合理（百分比/时间数值非拍脑门）
- 两种角色内容无矛盾（如库内说A，中台说B）
- 托盘级别一致性：无箱级/件级操作描述
- 入库起点一致性：无港口→仓库段描述
- 出库端仓库职责：只做核实确认，不涉及调度指派

- [ ] **Step 2: 打印验证**

在浏览器打开 `德国仓执行SOP_v1.html`：
- Ctrl+P 预览，确认所有8个节点内容全部显示
- 确认两种角色（库内+中台）内容在打印版中同时可见
- 确认左侧导航在打印版中隐藏
- 确认角色切换标签在打印版中隐藏
- 确认页面分页合理（每个节点尽量不被截断）

- [ ] **Step 3: 检查页脚版本信息**

确认Footer包含：
- 版本号：v1 (测试版)
- 日期：2026-08-04
- 修订记录表：至少包含A1初版记录

- [ ] **Step 4: 清理临时文件**

```bash
rm temp_docx_extract.txt
```

- [ ] **Step 5: Commit 定稿**

```bash
git add 德国仓执行SOP_v1.html
git commit -m "chore: SOP v1测试版定稿 — 内容复核+打印验证通过"
```

---

## Post-Implementation

v1测试版发布后，在实际使用中收集反馈，迭代修订：
1. 收集德国现场和中台的使用反馈
2. 补充现场实拍照片（现阶段为纯文字）
3. 修订内容 → 升级版本号（A2, A3...）
4. 完成测试后导出 `德国仓执行SOP_v最终版.pdf`
