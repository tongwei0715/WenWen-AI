# WenWen AI 品牌层说明

本仓库是 [TencentCloud/Octop](https://github.com/TencentCloud/Octop) 的二次开发分支，
品牌为 **WenWen AI**。品牌改动被收敛在一套可重复执行的脚本里，
同步官方更新后重新运行即可恢复品牌，不会被覆盖。

> 项目简介、功能说明与部署方式以上游仓库为准：
> 上游 README（[中文](https://github.com/TencentCloud/Octop/blob/main/README_CN.md) /
> [English](https://github.com/TencentCloud/Octop/blob/main/README.md)）、
> 上游 `docs/` 与 `CHANGELOG.md`。
> 本仓库与上游的差异只有品牌层（见下）与 `CHANGELOG-WENWEN.md` 记录的版本变更；
> 部署时把上游文档里的包名/镜像名/CLI 换成 `wenwen-ai` / `wenwen` 即可，
> 其余步骤与上游完全一致。

## 品牌内容

| 项目 | 说明 |
|---|---|
| 显示名 | WenWen AI |
| Logo | 黑色对话气泡 + 白色 W，黑白极简风（`branding/assets/` 为 SVG 母版） |
| 主题 | 新增 `openai` monochrome 色板并设为默认；原 `rose` 等色板保留，可在设置里切换 |
| 发行包名 | `wenwen-ai`（PyPI / wheel） |
| CLI | `wenwen`（`octop` 保留为兼容别名） |
| Web 标题 / 登录 / 引导页 | WenWen AI + 新 logo |
| 桌面端（Wails） | 产品名 WenWen AI，二进制/包名 WenWenAI，便携包 WenWenAI-portable-* |
| 动画 mascot | 原章鱼 peek/type 动画已替换为静态 WenWen 标识（`<img>` 用法不变） |

## 刻意保留 `octop` 的地方（不要改）

同步时零冲突的关键：以下内部标识保持原样，用户不可见。

- Python 包名 `src/octop` 及其内部 `import`
- 数据目录 `~/.octop`、`OCTOP_HOME`、`octop.db`
- localStorage 键（如 `octop:ui-palette`）、CSS 类名、API 路由、`X-Octop-*` 请求头
- 上游依赖名：`octop-harness` / `octop-gateway` / `octop-memory` / `octop-browser`
- `CHANGELOG.md`（历史记录）
- 桌面端 Go 标识符（`startOctop` 等）、`X-Octop-*` 相关类型名（`OctopAgent` 等）
- 技能模板里的功能性 `octop:` YAML key

## 文件布局

```
branding/
  assets/                 # logo SVG 母版（icon / 横版 / mascot / banner）
  tools/render-logos.mjs  # SVG -> PNG 渲染（node + @resvg/resvg-js）
scripts/apply-branding.py # 品牌应用脚本（幂等，可重复运行）
BRANDING.md               # 本文档
```

`dashboard/public/logo_horizontal_*.png`、`docs/assets/readme-banner*.png` 等 PNG
由 SVG 母版渲染得到；改 SVG 后运行 `node branding/tools/render-logos.mjs` 重新生成。

## 同步官方更新（不会丢品牌）

完整操作流程，每次同步官方更新都按此执行：

```bash
# 1. 取官方更新
git fetch upstream

# 2. 合并到当前分支（main）
git merge upstream/main
```

**出现合并冲突时的处理原则：**

| 冲突文件类型 | 处理方式 |
|---|---|
| 品牌脚本/品牌资源（`scripts/apply-branding.py`、`branding/`、`BRANDING.md`） | 以本仓库版本为准（`git checkout --ours`），品牌逻辑由我们维护 |
| 官方功能文件（如 `dashboard/src/...`、`src/octop/...` 被官方重构） | 以官方为准（`git checkout --theirs`），合并完成后再跑第 3 步恢复品牌 |
| 文案/标题类冲突 | 先合入官方，跑脚本后检查一遍页面文案即可 |

```bash
# 3. 重新应用品牌（幂等：已是品牌状态则无输出）
python scripts/apply-branding.py

# 4. 品牌自检（应无输出）
python scripts/apply-branding.py --check

# 5. 重新构建前端（dashboard 有改动时）
make build-frontend

# 6. 验证
cd dashboard && npx tsc -b
uv run pytest tests/unit/i18n -q
# 条件允许时跑全量：make all

# 7. 记录本次更新（必须）
#    在 CHANGELOG-WENWEN.md 顶部新增一条，写明：上游版本、同步日期、
#    品牌脚本是否需要调整、本次改了什么

# 8. 提交（品牌与合并分开，便于回看）
git add -A
git commit -m "chore: merge upstream <上游版本>"
python scripts/apply-branding.py   # 确认无残留后
git commit -m "branding: re-apply WenWen AI branding after upstream sync"
```

**为什么品牌不会被覆盖：**

1. 所有用户可见的品牌改动都由 `scripts/apply-branding.py` 生成，
   合并官方代码后重跑一次即恢复——脚本是幂等的，可反复执行。
2. 品牌相关的提交独立存放（`git log --grep=branding` 可查），
   不混入功能合并提交。
3. 内部标识（`src/octop`、`~/.octop`、`octop.db` 等）刻意不改，
   官方重构内部代码时几乎不产生冲突。
4. `CHANGELOG-WENWEN.md` 记录每次同步的版本与变更，可追溯。

## 改了品牌相关的东西？

- 改了 SVG 母版 → 跑 `node branding/tools/render-logos.mjs`
- 加了新的用户可见文案 → 文案进 `dashboard/src/locales/{zh,en}.json`
  或 `src/octop/i18n/{zh,en}.json`（中英 key 对齐），再跑一遍脚本
- 想换默认色 → 改 `dashboard/src/styles/themePalettes.ts` 的 `DEFAULT_PALETTE`

## 验证清单

- `python scripts/apply-branding.py --check` 无输出（已是品牌状态；`--check` 为纯只读，不写 PNG）
- `cd dashboard && npx tsc -b` 通过
- `uv run pytest tests/unit/i18n -q` 通过（中英 key 对齐）
- 桌面端：`cd desktop/src && go test ./...` 通过（品牌断言与源码文案一致）
- 页面标题、登录页、引导页显示 WenWen AI；设置 → 外观默认选中 `openai`（墨黑）色板
