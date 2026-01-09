#!/bin/bash
set -e

PROJECT_ROOT="$(pwd)"
BASE_DIR="$(dirname "$PROJECT_ROOT")"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

check_git() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo "Not in a git repository"
        exit 1
    fi
}

list_worktrees() {
    info "Current Git Worktrees:"
    git worktree list
    echo ""
    info "Branches:"
    git branch -a
}

create_dev_worktrees() {
    info "Creating development worktrees..."

    if [ ! -d "$BASE_DIR/work-scraper" ]; then
        git worktree add "$BASE_DIR/work-scraper" -b feature/scraper-v4
        info "✓ Created work-scraper (爬虫开发)"
    else
        warn "work-scraper already exists"
    fi

    if [ ! -d "$BASE_DIR/work-tools" ]; then
        git worktree add "$BASE_DIR/work-tools" -b feature/tools
        info "✓ Created work-tools (工具开发)"
    else
        warn "work-tools already exists"
    fi

    if [ ! -d "$BASE_DIR/work-tests" ]; then
        git worktree add "$BASE_DIR/work-tests" -b feature/tests
        info "✓ Created work-tests (测试开发)"
    else
        warn "work-tests already exists"
    fi

    if [ ! -d "$BASE_DIR/work-experiment" ]; then
        git worktree add "$BASE_DIR/work-experiment" -b experiment/sandbox
        info "✓ Created work-experiment (实验功能)"
    else
        warn "work-experiment already exists"
    fi

    if [ ! -d "$BASE_DIR/work-ui" ]; then
        git worktree add "$BASE_DIR/work-ui" -b feature/web-ui-v3
        info "✓ Created work-ui (UI/Web 开发)"
    else
        warn "work-ui already exists"
    fi

    echo ""
    list_worktrees
}

create_hotfix() {
    if [ -z "$1" ]; then
        echo "Usage: $0 hotfix <issue-name>"
        exit 1
    fi

    HOTFIX_NAME="hotfix/$1"
    HOTFIX_DIR="$BASE_DIR/hotfix-$1"

    info "Creating hotfix worktree for $1..."

    if [ -d "$HOTFIX_DIR" ]; then
        echo "Hotfix directory already exists: $HOTFIX_DIR"
        exit 1
    fi

    git worktree add "$HOTFIX_DIR" -b "$HOTFIX_NAME" master
    info "✓ Created $HOTFIX_DIR"

    echo ""
    info "Next steps:"
    echo "  cd $HOTFIX_DIR"
    echo "  # ... fix the bug ... "
    echo "  git commit -am 'fix: $1'"
    echo "  git checkout master"
    echo "  git merge $HOTFIX_NAME"
    echo "  git worktree remove $HOTFIX_DIR"
}

clean_worktrees() {
    info "Pruning deleted branches..."
    git worktree prune

    info "Current worktrees:"
    git worktree list
}

remove_worktree() {
    if [ -z "$1" ]; then
        echo "Usage: $0 remove <worktree-path>"
        exit 1
    fi

    info "Removing worktree: $1"
    git worktree remove "$1"
    info "✓ Removed"
}

show_help() {
    cat << HELP
Git Worktree 管理脚本

用法: $0 [command] [options]

命令:
  list                列出所有工作区
  create              创建开发工作区
  hotfix <name>       创建 hotfix 工作区
  remove <path>       移除工作区
  clean               清理已删除分支的工作区
  help                显示此帮助
HELP
}

main() {
    check_git

    case "${1:-help}" in
        list)
            list_worktrees
            ;;
        create)
            create_dev_worktrees
            ;;
        hotfix)
            create_hotfix "$2"
            ;;
        remove)
            remove_worktree "$2"
            ;;
        clean)
            clean_worktrees
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
