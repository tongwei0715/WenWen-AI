# WenWen AI 更新日志

本文件记录 WenWen AI 在官方上游版本基础上的**品牌与定制变更**。
上游官方的版本变更见 [`CHANGELOG.md`](./CHANGELOG.md)（保持原样，不修改）。

版本号规则：`<上游版本>-wenwen.<N>`，例如 `1.0.2b7-wenwen.1` 表示
基于上游 `1.0.2b7` 的第 1 个 WenWen AI 品牌版本。

> 约定：每次同步官方更新或修改品牌后，都在文件顶部新增一条记录，
> 写明上游版本、日期、变更内容与同步说明。

---

## [1.0.2b9-wenwen.13] - 2026-10-18

合入上游 `v1.0.2b9`（39 个提交）：
- ONNX 模型离线加载（不依赖 Hugging Face API）
- 中文优先的业务流程专家、技能包导出为 ZIP、记忆手动画像与冲突复核
- 通道插件安装与运行生命周期打通、技能/工具/团队决策模型
- Agent 健康感知的模型故障转移、Agent MCP 网关
- Docker 镜像包含本地知识库运行时；FnOS beta 版本编码修复应用商店升级
- Dashboard：对话专家置顶、远程插件缺失提示
- 修复：fd 限制、grep 防 OOM、peer composer 默认值等
- 冲突解决（4 个文件）：docker README 保留 `--name wenwen` 并取上游
  `--ulimit`；`pyproject.toml` 保留 `name = "wenwen-ai"` 取上游
  `version = "1.0.2b9"` 与依赖升级（octop-harness→1.0.4、
  octop-gateway→1.0.3）；`uv.lock` 重生成
- branding 脚本全量重刷，`--check` 干净

## [Unreleased]

- 修复 Windows 任务栏图标仍为旧 Octop 红标：`desktop/src/assets/tray-icon.png`
  一直是上游的红色图标（Wails 用它做任务栏/窗口图标），`make-desktop-assets.py`
  漏了它；现已用黑白品牌重绘，并一并重绘 macOS 用的 `tray-icon-template.png`，
  生成器与 branding 脚本注释已同步
- 新增 `.github/workflows/upstream-sync.yml`：每周一 09:00（CST）自动检查
  上游 `TencentCloud/Octop` 新提交并试合并；能干净合并则跑 branding +
  `make test` 验证，任一环节失败则 run 标红。只检测、不开 PR、不建 issue、
  绝不直接推 main；通知由外部盯哨读取 run 结果后发出
- FnOS FPK 构建与 Release 页面修复方案（计划中，代码尚未落地）：
  - `scripts/build-fpk.sh` 新增 `FPK_IMAGE`（完整 repo:tag 覆盖上游镜像地址）
    与 `FPK_VERSION`（覆盖版本号解析），默认保持上游行为不变
  - `fnos/native/app/bin/octop{,-cli}` 按 `wenwen_ai-*.whl` 查找内置 wheel
    （pip 要求合法 wheel 文件名，不能像上游那样重命名为 `octop.whl`）
  - `fnos-build-fpk.yml` 把 workflow 已算好的 fork 镜像名传给 `FPK_IMAGE`；
    `apply-branding.py` 加镜像地址规则
  - `release.yml` Release 说明的安装命令改为
    `pip install "wenwen-ai @ git+https://github.com/tongwei0715/WenWen-AI@v<tag>"`；
    `scripts/release_download_links.py` 仓库指向 fork、产物文件名 `WenWenAI-*`

## [1.0.2b8-wenwen.12] - 2026-10-16

合入上游 `v1.0.2b8`（对话中途转向、专家记忆备份/恢复与存储维护、
Telegram 频道可限制用户 ID、语雀网关连接器、bridge 多 peer 与隧道传附件，
以及 Windows 记忆备份恢复、微信定时任务、知识库上限等多项修复）：
- `pyproject.toml`：保留 `name = "wenwen-ai"` 与品牌描述，取上游
  `version = "1.0.2b8"` 与依赖变更（octop-harness→1.0.3、octop-gateway→1.0.2、
  新增 firecrawl-anydoc 等）；`uv.lock` 同步
- README / 前端新文案冲突均按"取上游功能、刷 WenWen AI 品牌"解决，
  branding 脚本重新全量刷过
- **剔除 b8 新增的 COS 上传**：`octop-desktop.yml` / `fnos-build-fpk.yml` 的
  `upload-cos` job、`upload-release-cos.yml`、`scripts/ci/upload_release_cos.sh`
  全部删除（fork 无 COS 凭证，且 `Octop-*` 文件名模式匹配不到 `WenWenAI-*`
  产物，留着每轮构建必红）；branding 脚本加锁定规则防上游合回

## [1.0.2b7-wenwen.11] - 2026-10-16

桌面包视觉品牌补完（用户下载安装包验证发现残留旧红色 Octop 图标与标题）：
- 应用图标换成黑白 WenWen AI：`desktop/src/build/appicon.png`、
  `appicon-macos.png`（新增可复现生成脚本 `branding/make-desktop-assets.py`）
- Windows：exe 文件属性、`info.json`、NSIS 安装标题/产品名、manifest identity
- macOS：`Info.plist`/`Info.dev.plist` 应用名与 bundle ID、DMG 背景文案
  （"Drag WenWen AI to your Applications folder"）
- 修复两个 macOS 真 bug：`CFBundleExecutable` 与实际 `WenWenAI` 二进制名不
  一致导致 Finder 可能无法启动；Resources 内 portable zip 仍为
  `Octop-darwin-*` 而程序只找 `WenWenAI-*`，导致找不到 runtime
- Actions workflow 显示名 `Octop Desktop Package` → `WenWen AI Desktop Package`
- branding 脚本加锁定规则，防上游合并回退以上改动。

## [1.0.2b7-wenwen.10] - 2026-10-14

桌面版 CI workflow fork 化：`octop-desktop.yml` 仍在找上游 `Octop-*`
产物名，而打包脚本实际产出 `WenWenAI-*`，CI 会直接失败。
已改为 `WenWenAI-*`（portable/desktop/staging/download pattern），
产物版本号改读 `wenwen_version.py` 的 fork 版本号；
branding 脚本锁定这些改动防上游合并回退。
打 tag `v1.0.2b7-wenwen.10` 即可触发六平台桌面包构建并挂到 GitHub Release。

## [1.0.2b7-wenwen.9] - 2026-10-14

**升级链路 fork 化（修复在线升级抹掉品牌的问题）**：
- 根因：`self_update.py` 的 `_PACKAGE_NAME` 写死为上游 `octop`，
  前端"在线升级"实际执行 `pip install -U octop`，把品牌包整个换成上游原版；
  且包改名后本地版本号读不到（返回 `0.0.0`），导致永远提示有更新。
- `_PACKAGE_NAME` 改为 `wenwen-ai`；新增 `src/octop/wenwen_version.py`
 （`WENWEN_VERSION`/`WENWEN_REPO`，由 `apply-branding.py` 从本日志同步），
  更新检查改为查询 fork 自身的 GitHub releases（`fetch_fork_release()`），
  不再碰 PyPI 的上游包。
- 源码安装（editable 或 `file://` 直接安装）拦截：`run_upgrade()`、
  `/api/update/upgrade`、CLI `wenwen update` 均拒绝 pip 升级并提示
  `git pull`；前端新增 `is_source_install` 状态，隐藏升级按钮并显示指引。
- 非源码安装的升级改为从 fork GitHub 按 release tag 安装
 （`wenwen-ai @ git+https://github.com/<fork>@<tag>`）。
- 测试同步更新（CLI/router/self_update 均改为 fork 行为断言）；
  branding 脚本新增 `apply_wenwen_version()` 并锁定关键标记，
  上游合并若破坏这些改动会被 `--check` 指出。

## [1.0.2b7-wenwen.8] - 2026-10-14

品牌全量自检补漏：新增 `apply_dashboard_string_literals()`
（分词器级横扫 dashboard 全部 ts/tsx 字符串字面量，跳过注释/
标识符/路径/URL），补上之前逐字替换表漏掉的用户可见文案：
PWA manifest 安装名、`apple-mobile-web-app-title`、offline.html、
ChatInput 占位符、记忆/连接器/远程桌面/更新页等 10+ 处；
`catalog.json` 连接器描述 4 处（surgical 替换，不重排格式）；
`process_test.go` 断言对齐；`UpdateConfig` 里 `cd Octop` →
`cd WenWen-AI`；修正旧版误换的 `wenwen[browser]` →
`wenwen-ai[browser]`（pip 包名）。有意不碰：Ant Design
`prefixCls="octop"`（LESS 样式依赖）、postgres 默认库名/用户
名（功能配置）、`octop.db` / `~/.octop` / `OCTOP_HOME`。
已验证：脚本二次运行零改动（完全幂等）；模拟上游新增
Octop 字符串 → `git merge` 无冲突 → 重跑脚本自动品牌化。

## [1.0.2b7-wenwen.7] - 2026-10-14

P2 补幂等：`scripts/apply-branding.py` 的 `apply_desktop()` 里
`download_test.go` 之前只替换 `.zip` 文件名，错误文案断言
（"Octop 服务未在…" 等）上游合并后不会被恢复。新增加
`re.sub(r"(?<![\w/-])Octop(?![\w-])", DISPLAY, text)` 规则；
已用"回滚→重跑脚本"实测验证：断言恢复为 "WenWen AI"，
`Octop-test/` 等测试固件路径有意保留。

## [1.0.2b7-wenwen.6] - 2026-10-14

桌面端加载页章鱼吉祥物替换：`desktop/src/assets/index.html`
引用的 `octop-mascot-peek.webp` / `octop-mascot-type.webp`
换成新 logo 生成的 `wenwen-mascot-peek.webp` / `wenwen-mascot-type.webp`；
旧 webp 已删除并加入脚本 retire 列表；该页面标题/品牌文案
"Octop" → "WenWen AI"；`scripts/apply-branding.py`
新增该文件的处理及 webp 生成逻辑。

## [1.0.2b7-wenwen.5] - 2026-10-14

品牌审计修复：补齐 5 处遗漏。

### 修复

- **P1**：`docs/user-guide.html` 13 处 "Octop" 补品牌化；
  `scripts/apply-branding.py` 新增该文件的处理（`prose_rules`）。
- **P2**：`desktop/src/download_test.go` 健康检查断言文案
  改为 "WenWen AI …"（与 `desktop_copy.go` 源码一致）。
- **P3**：`.github/workflows/fnos-build-fpk.yml` 产物前缀
  `Octop-fnos` → `WenWenAI-fnos`；README/README_CN、
  desktop/README、fnos/README 产物表同步为 `WenWenAI-desktop-*` /
  `WenWenAI-fnos-*`。
- **P4**：删除死资源 `docs/assets/octop-banner.png`（153KB，无引用），
  并加入脚本 retire 列表。
- **P5**：`--check` 改为纯只读（不再触发 node PNG 渲染）；
  验证清单新增 `go test`。

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
