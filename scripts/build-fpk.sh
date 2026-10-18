#!/usr/bin/env bash
# =============================================================================
# 构建 Octop 飞牛 FnOS 安装包 (.fpk)
#
# 直接使用官方 fnpack CLI 打包（fnpack 在生成 .fpk 前会校验 manifest / cmd /
# config / wizard / app 等结构，确保产物与飞牛 fnOS 安装校验完全一致）。
#
# 用法（在仓库根目录执行):
#   bash scripts/build-fpk.sh docker      # 构建 Docker 版  -> dist/Octop-fnos-docker-<ver>.fpk
#   bash scripts/build-fpk.sh native      # 构建本地版(非Docker) -> dist/Octop-fnos-native-<ver>.fpk
#   bash scripts/build-fpk.sh             # 两个都构建
#
# 环境变量：
#   FPK_NAME_PREFIX  输出文件名前缀，默认 "octop"
#                    例如 FPK_NAME_PREFIX=Octop-fnos 会生成 Octop-fnos-docker-<ver>.fpk / Octop-fnos-native-<ver>.fpk
#   FPK_ITER         迭代号，默认空
#                    例如 FPK_ITER=01 会生成 ...-<ver>-01.fpk（通常不需要，按版本号发布）
#   FPK_ARCH         本地版架构。arm64 → Octop-fnos-native-arm64-<ver>.fpk，
#                    并写入 manifest platform=arm（fnpack 只认 x86/arm/all）。空或其它值保持现有 x86 包名。
#                    fnpack 官方只有 linux-amd64，ARM 包应在 amd64 主机上打包
#                    （site-packages 先在 aarch64 上装好再拷过来）。
#   FPK_VERSION      覆盖版本号（默认从 pyproject.toml 解析）。
#                    fork 发版时传入完整 fork 版本（如 1.0.2b9-wenwen.13），
#                    使包名/镜像标签与 Release tag 对齐；manifest 写入的商店
#                    可比版本会自动剥掉 -wenwen.N 后缀再编码。
#   FPK_IMAGE        Docker 版 compose 镜像完整地址（repo:tag），
#                    默认 "ghcr.io/tencentcloud/octop:<tag>"（上游行为不变）。
#                    fork 构建时传入如 ghcr.io/tongwei0715/wenwen-ai:1.0.2b9-wenwen.13。
#
# 说明：
#   - Linux CI 下会自动下载 fnpack（版本见 FNPACK_VERSION，默认 1.2.3）；
#     curl 对 RST / 超时等瞬时错误重试。成功后落到 .verify/fnpack 供本机与
#     Actions cache 复用。
#   - 本地若已存在 .verify/fnpack(.exe) 则直接复用，不再联网下载。
#   - 版本号来自仓库根 pyproject.toml。镜像标签与包名仍用该 PEP 440 字符串。
#     写入 manifest 的是商店可比版本（1.0.2b8 → 1.0.208），见
#     scripts/fnos/store_version.sh。manifest 为 key=value 无空格格式。
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/dist"

# 使用仓库内的临时目录，避免 Windows 风格 TMPDIR 在 Git Bash 下被错误解析
TMP="$(mktemp -d "$ROOT/.buildtmp.XXXXXX")"
cleanup() { rm -rf "$TMP" >/dev/null 2>&1 || true; }
trap cleanup EXIT

# Accept full PEP 440 strings in quotes (e.g. 1.0.2b1), not digits-only.
# FPK_VERSION overrides the parsed version (fork releases pass the full
# fork version, e.g. 1.0.2b9-wenwen.13, so artifact names match the tag).
VER="${FPK_VERSION:-$(sed -nE 's/^version[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' "$ROOT/pyproject.toml" | head -1)}"
[ -n "$VER" ] || { echo "无法解析版本（pyproject.toml 或 FPK_VERSION）"; exit 1; }
case "$VER" in
  *[[:space:]]*|*[\"\']*)
    echo "解析到的版本非法: $VER"
    exit 1
    ;;
esac
# shellcheck source=scripts/fnos/store_version.sh
source "$ROOT/scripts/fnos/store_version.sh"
# 商店版本只认 X.Y.Z / X.Y.ZbN：fork 后缀（-wenwen.N）先剥掉再编码，
# manifest 写 1.0.209 这类可比版本；包名与镜像标签仍用完整 $VER。
STORE_VER="$(fnos_store_version "${VER%%-wenwen.*}")"
echo "[build-fpk] Octop 版本: $VER (飞牛商店: $STORE_VER)"

# 输出文件名前缀与迭代号（由 CI 传入，实现 Octop-fnos-docker-0.9.30.fpk 风格）
PREFIX="${FPK_NAME_PREFIX:-octop}"
ITER_SUFFIX=""
if [ -n "${FPK_ITER:-}" ]; then
  ITER_SUFFIX="-$FPK_ITER"
fi
echo "[build-fpk] 包名前缀: $PREFIX, 迭代后缀: ${ITER_SUFFIX:-<none>}"

# --- 获取 fnpack CLI ---
# Keep FNPACK_VERSION in sync with .github/workflows/fnos-build-fpk.yml cache key.
FNPACK_VER="${FNPACK_VERSION:-1.2.3}"
VERIFY_DIR="$ROOT/.verify"
mkdir -p "$VERIFY_DIR"
if [ -f "$VERIFY_DIR/fnpack.exe" ]; then
  chmod +x "$VERIFY_DIR/fnpack.exe" 2>/dev/null || true
fi
if [ -f "$VERIFY_DIR/fnpack" ]; then
  chmod +x "$VERIFY_DIR/fnpack" 2>/dev/null || true
fi
FNPACK=""
if [ -x "$VERIFY_DIR/fnpack.exe" ]; then
  FNPACK="$VERIFY_DIR/fnpack.exe"
elif [ -x "$VERIFY_DIR/fnpack" ]; then
  FNPACK="$VERIFY_DIR/fnpack"
else
  OS="$(uname -s)"
  case "$OS" in
    Linux)  FNPACK_URL="https://static2.fnnas.com/fnpack/fnpack-${FNPACK_VER}-linux-amd64" ;;
    Darwin) FNPACK_URL="https://static2.fnnas.com/fnpack/fnpack-${FNPACK_VER}-darwin-amd64" ;;
    *)      FNPACK_URL="https://static2.fnnas.com/fnpack/fnpack-${FNPACK_VER}-windows-amd64" ;;
  esac
  case "$OS" in
    Linux|Darwin) FNPACK="$VERIFY_DIR/fnpack" ;;
    *)            FNPACK="$VERIFY_DIR/fnpack.exe" ;;
  esac
  echo "[build-fpk] 下载 fnpack: $FNPACK_URL"
  curl -fsSL --connect-timeout 20 --max-time 120 \
    --retry 5 --retry-delay 2 --retry-all-errors \
    -o "${FNPACK}.partial" "$FNPACK_URL"
  mv "${FNPACK}.partial" "$FNPACK"
  chmod +x "$FNPACK"
  if [ ! -s "$FNPACK" ]; then
    echo "[build-fpk] 下载的 fnpack 为空: $FNPACK_URL"
    rm -f "$FNPACK"
    exit 1
  fi
fi
echo "[build-fpk] 使用 fnpack: $FNPACK"

mkdir -p "$OUT"

build_one() {
  local KIND="$1" PKG OUTNAME
  case "$KIND" in
    docker)
      PKG="$ROOT/fnos/docker"
      OUTNAME="${PREFIX}-docker-${VER}${ITER_SUFFIX}.fpk"
      ;;
    native)
      PKG="$ROOT/fnos/native"
      if [ "${FPK_ARCH:-}" = "arm64" ]; then
        OUTNAME="${PREFIX}-native-arm64-${VER}${ITER_SUFFIX}.fpk"
      else
        OUTNAME="${PREFIX}-native-${VER}${ITER_SUFFIX}.fpk"
      fi
      ;;
    *) echo "未知类型: $KIND"; return 1 ;;
  esac

  local BUILD="$TMP/$KIND"
  rm -rf "$BUILD"; mkdir -p "$BUILD"

  # 复制整个包目录（manifest / cmd / config / wizard / app / ICON* / LICENSE）
  cp -r "$PKG/." "$BUILD/"

  # 注入共享函数库（find_python312 / fix_ownership_and_perms / free_octop_ports），
  # 仓库单一来源 scripts/fnos/common.sh，cmd/bin 脚本统一 source cmd/common.sh。
  if [ -f "$ROOT/scripts/fnos/common.sh" ]; then
    cp "$ROOT/scripts/fnos/common.sh" "$BUILD/cmd/common.sh"
  fi

  # 商店只比较 x.y.z。manifest 写编码后的版本，compose 镜像标签仍用 $VER。
  sed -i.bak "s/^version=.*/version=$STORE_VER/" "$BUILD/manifest" && rm -f "$BUILD/manifest.bak"
  echo "[build-fpk] manifest version=$STORE_VER"

  # ARM 本地版写入 fnpack 允许的 platform=arm；更细的 aarch64 用 cmd/fpk-arch。
  if [ "$KIND" = "native" ] && [ "${FPK_ARCH:-}" = "arm64" ]; then
    sed -i.bak "s/^platform=.*/platform=arm/" "$BUILD/manifest" && rm -f "$BUILD/manifest.bak"
    echo "[build-fpk] native manifest platform=arm"
  fi

  # 本地版写入架构标记，安装/启动时对一下，避免装错包。
  if [ "$KIND" = "native" ]; then
    local packed_arch
    case "${FPK_ARCH:-}" in
      arm64) packed_arch=arm64 ;;
      amd64) packed_arch=amd64 ;;
      *)
        case "$(uname -m)" in
          aarch64|arm64) packed_arch=arm64 ;;
          *) packed_arch=amd64 ;;
        esac
        ;;
    esac
    printf '%s\n' "$packed_arch" > "$BUILD/cmd/fpk-arch"
    echo "[build-fpk] native cmd/fpk-arch=$packed_arch"
  fi

  # Docker 版 compose 钉镜像。默认与本包同版本的上游地址；测试包可用
  # FPK_IMAGE_TAG=latest 只覆盖标签；fork 用 FPK_IMAGE=<完整 repo:tag>
  # 直接覆盖整个地址（未设置时保持上游默认行为）。
  if [ "$KIND" = "docker" ]; then
    local compose="$BUILD/app/docker/docker-compose.yaml"
    local image_ref="${FPK_IMAGE:-ghcr.io/tencentcloud/octop:${FPK_IMAGE_TAG:-$VER}}"
    if [ -f "$compose" ]; then
      sed -i.bak -E "s#image:[[:space:]]*ghcr\.io/[^[:space:]\'\"]+#image: ${image_ref}#" "$compose"
      rm -f "${compose}.bak"
      echo "[build-fpk] compose 镜像: ${image_ref}"
    fi
  fi

  echo "[build-fpk] fnpack 校验并打包 $KIND ..."
  # fnpack 校验 manifest/cmd/config/wizard/app 后在当前目录生成 <appname>.fpk
  # Windows 版 fnpack.exe 无法解析 Git-Bash 的 /c/... 路径，需转换为 Windows 原生路径。
  local DIR="$BUILD"
  case "$FNPACK" in
    *.exe) DIR="$(cygpath -w -m "$BUILD")" ;;
  esac
  ( cd "$BUILD" && "$FNPACK" build --directory "$DIR" )

  local SRC
  SRC="$(ls "$BUILD"/*.fpk 2>/dev/null | head -1)"
  [ -n "$SRC" ] || { echo "[build-fpk] 未找到 fnpack 产物"; return 1; }

  mv "$SRC" "$OUT/$OUTNAME"
  echo "[build-fpk] 产物: $OUT/$OUTNAME ($(stat -c%s "$OUT/$OUTNAME") bytes)"
  echo "[build-fpk] 外层内容:"
  tar -tzf "$OUT/$OUTNAME"
}

if [ $# -eq 0 ]; then
  build_one docker
  build_one native
else
  for k in "$@"; do build_one "$k"; done
fi
