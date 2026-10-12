# WenWen AI 品牌层说明

本仓库是 [TencentCloud/Octop](https://github.com/TencentCloud/Octop) 的二次开发分支，
品牌为 **WenWen AI**。品牌改动被收敛在一套可重复执行的脚本里，
同步官方更新后重新运行即可恢复品牌，不会被覆盖。

## 品牌内容

| 项目 | 说明 |
|---|---|
| 显示名 | WenWen AI |
| Logo | 几何 "W" + 灵感火花点，黑白极简风（`branding/assets/` 为 SVG 母版） |
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

```bash
# 1. 取官方更新
git fetch upstream
git merge upstream/main        # 有冲突时：品牌文件以官方为准，合并完继续第 2 步

# 2. 重新应用品牌（幂等）
python scripts/apply-branding.py

# 3. 重新构建前端（dashboard 有改动时）
make build-frontend

# 4. 验证
make all
```

建议把品牌改动保持在独立提交里（`git log --grep=branding`），
与功能性合并分开，便于回看。

## 改了品牌相关的东西？

- 改了 SVG 母版 → 跑 `node branding/tools/render-logos.mjs`
- 加了新的用户可见文案 → 文案进 `dashboard/src/locales/{zh,en}.json`
  或 `src/octop/i18n/{zh,en}.json`（中英 key 对齐），再跑一遍脚本
- 想换默认色 → 改 `dashboard/src/styles/themePalettes.ts` 的 `DEFAULT_PALETTE`

## 验证清单

- `python scripts/apply-branding.py --check` 无输出（已是品牌状态）
- `cd dashboard && npx tsc -b` 通过
- `uv run pytest tests/unit/i18n -q` 通过（中英 key 对齐）
- 页面标题、登录页、引导页显示 WenWen AI；设置 → 外观默认选中 `openai`（墨黑）色板
