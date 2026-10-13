# WenWen AI 更新日志

本文件记录 WenWen AI 在官方上游版本基础上的**品牌与定制变更**。
上游官方的版本变更见 [`CHANGELOG.md`](./CHANGELOG.md)（保持原样，不修改）。

版本号规则：`<上游版本>-wenwen.<N>`，例如 `1.0.2b7-wenwen.1` 表示
基于上游 `1.0.2b7` 的第 1 个 WenWen AI 品牌版本。

> 约定：每次同步官方更新或修改品牌后，都在文件顶部新增一条记录，
> 写明上游版本、日期、变更内容与同步说明。

---

## [1.0.2b7-wenwen.4] - 2026-10-13

Logo 右上角增加小写 `ai` 圆点角标。

### 变更

- **ai 角标**：对话气泡右上角加黑色圆点徽章（白字 `ai`），
  深/浅两版各有对应配色；更新全部 7 个 SVG 母版并重新渲染 PNG，
  经 `scripts/apply-branding.py` 同步到登录页、侧边栏、favicon、
  空状态插画、README banner、渠道图标。

## [1.0.2b7-wenwen.3] - 2026-10-13

去掉空状态 mascot 后面的灰色圆圈，只保留对话气泡图标。

### 变更

- **mascot 去圆圈**：`branding/assets/wenwen-mascot.svg` 去掉灰色圆底，
  纯对话气泡图标（透明背景）；重新渲染
  `wenwen-mascot-empty.png` / `wenwen-mascot-tasks.png`，
  影响空状态页、输入框思考气泡、连接中指示器。

## [1.0.2b7-wenwen.2] - 2026-10-13

Logo 更换：由"几何 W + 灵感火花点"改为"黑色对话气泡 + 白色 W"。

### 变更

- **新 Logo**：对话气泡造型，一眼可识别为 AI 聊天；保持黑白极简风。
  更新了 `branding/assets/` 下全部 7 个 SVG 母版
  （icon 深/浅、横版深/浅、mascot、banner 中/英），
  并重新渲染了所有 PNG（`node branding/tools/render-logos.mjs`），
  通过 `scripts/apply-branding.py` 同步到登录页、侧边栏、启动屏、
  favicon、空状态插画、README banner、渠道图标。
- **版本记录机制**：今后每次 logo/品牌变更都在此记录（用户要求）。

## [1.0.2b7-wenwen.1] - 2026-10-13

首个品牌化版本，基于上游 `TencentCloud/Octop` v1.0.2b7。

### 新增

- **新 Logo**：几何 "W" + 顶部灵感火花点，黑白极简风。
  SVG 母版在 `branding/assets/`，PNG 由 `branding/tools/render-logos.mjs` 渲染。
  替换位置：登录页、侧边栏、启动屏、favicon、空状态插画、
  README banner、介绍页、渠道图标。
- **新主题**：`openai` monochrome 色板并设为默认（浅色黑按钮 / 深色白按钮，
  OpenAI 风格）；原 `rose` 等 8 个色板保留，可在设置 → 外观切换。
- **品牌脚本**：`scripts/apply-branding.py`（幂等）+ `BRANDING.md` 同步手册。
- **更新日志机制**：本文件，今后每次更新在此记录。

### 变更

- 发行包名 `octop` → `wenwen-ai`；CLI 新增 `wenwen`（`octop` 保留为兼容别名）。
- Web 标题、登录/引导页文案、文档、桌面端产品名（WenWen AI）、
  Docker 镜像名（`wenwen-ai`）统一品牌。
- 原章鱼 peek/type 动画 mascot 替换为静态 WenWen 标识（`<img>` 用法不变）。
- `docs/octop-introduction.html` → `docs/wenwen-introduction.html` 并换品牌。

### 刻意保留（用户不可见，避免同步冲突）

- Python 包 `src/octop`、内部 import、数据目录 `~/.octop`、`octop.db`、
  `OCTOP_HOME`、API 路由、`X-Octop-*` 请求头、localStorage 键。
- 上游依赖名：`octop-harness` / `octop-gateway` / `octop-memory` / `octop-browser`。
- `CHANGELOG.md` 上游历史记录。

### 同步说明

- 首次品牌化，无上游合并。
- 品牌改动收录于 `scripts/apply-branding.py`，今后同步官方更新后重跑即可恢复。
- 验证：前端 `tsc` 通过、主题测试 58/58、后端 i18n 80/80、CLI 相关 103 通过、
  生产构建成功；剩余失败项在官方原版同样存在（沙箱环境问题），与品牌无关。
