#!/usr/bin/env bash
# =============================================================================
# Leon Knowledge Base Template — Setup Script
#
# Usage:
#   ./setup.sh [TARGET_DIR]          部署 vault 骨架到 TARGET_DIR（默认 ~/ObsidianVault）
#   ./setup.sh --install-skill       安装 /record skill 到 ~/.claude/skills/record/
#   ./setup.sh --help                显示帮助
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES="$SCRIPT_DIR/templates"

show_help() {
  cat <<EOF
Leon Knowledge Base Template

Usage:
  ./setup.sh [TARGET_DIR]        部署 vault 到 TARGET_DIR（默认 \$HOME/ObsidianVault）
  ./setup.sh --install-skill     安装 /record skill 到 \$HOME/.claude/skills/record/
  ./setup.sh --help              显示本帮助

Example:
  ./setup.sh ~/Documents/MyVault
  ./setup.sh --install-skill

Notes:
  - 部署会跳过已存在的文件（不覆盖）
  - Vault 部署后请编辑 \$TARGET_DIR/Private-Vault/99_Meta/routing.md 把根路径改成你自己的
EOF
}

install_skill() {
  local skill_src="$TEMPLATES/claude-skill/record"
  local skill_dst="$HOME/.claude/skills/record"

  if [[ ! -d "$skill_src" ]]; then
    echo "❌ Skill source not found: $skill_src" >&2
    exit 1
  fi

  mkdir -p "$HOME/.claude/skills"
  if [[ -d "$skill_dst" ]]; then
    echo "⚠️  $skill_dst 已存在，跳过（手动删除后重跑可覆盖）"
    return
  fi

  cp -R "$skill_src" "$skill_dst"
  echo "✅ /record skill 安装到 $skill_dst"
  echo ""
  echo "下一步："
  echo "  1. 确认你的 vault 根路径（默认模板里是 \$HOME/ObsidianVault/Private-Vault）"
  echo "  2. 编辑 \$HOME/ObsidianVault/Private-Vault/99_Meta/routing.md 里的【根路径】字段"
  echo "  3. 在 Claude Code 里试一条：/record 今天试了新模板"
}

deploy_vault() {
  local target="${1:-$HOME/ObsidianVault}"
  target="${target/#\~/$HOME}"

  if [[ ! -d "$TEMPLATES/Private-Vault" ]]; then
    echo "❌ Templates not found: $TEMPLATES" >&2
    exit 1
  fi

  echo "📁 部署 vault 到: $target"
  mkdir -p "$target"

  # 复制 Private-Vault 和 Public-Vault 全部内容（不覆盖已存在文件）
  cp -Rn "$TEMPLATES/Private-Vault" "$target/" 2>/dev/null || true
  cp -Rn "$TEMPLATES/Public-Vault" "$target/" 2>/dev/null || true

  # 把所有 *.template 文件重命名去掉后缀（只对刚复制出来的目标）
  find "$target/Private-Vault" "$target/Public-Vault" -type f -name "*.template" 2>/dev/null | while read -r f; do
    local new="${f%.template}"
    if [[ ! -e "$new" ]]; then
      mv "$f" "$new"
    else
      rm "$f"  # 目标已存在则丢弃模板版本
    fi
  done

  # 替换 routing.md 里的 {{VAULT_ROOT}} 占位
  local routing="$target/Private-Vault/99_Meta/routing.md"
  if [[ -f "$routing" ]]; then
    # macOS / BSD sed 需要空后缀；Linux / GNU sed 不需要。两种都试
    sed -i '' "s|{{VAULT_ROOT}}|$target/Private-Vault|g" "$routing" 2>/dev/null || \
      sed -i "s|{{VAULT_ROOT}}|$target/Private-Vault|g" "$routing"
  fi

  echo "✅ Vault 骨架部署完成"
  echo ""
  echo "目录："
  ls -la "$target"
  echo ""
  echo "下一步："
  echo "  1. 用 Obsidian 打开 $target/Private-Vault 和 $target/Public-Vault"
  echo "  2. 按需改名：30_Work / 60_Hobby / 20_PhD → 你自己的类别"
  echo "  3. 运行 ./setup.sh --install-skill 安装 Claude Code skill"
}

# =============================================================================
# main
# =============================================================================

case "${1:-}" in
  --help|-h)
    show_help
    ;;
  --install-skill)
    install_skill
    ;;
  *)
    deploy_vault "${1:-}"
    ;;
esac
