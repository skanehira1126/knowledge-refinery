#!/bin/sh
set -eu

plugin_root=${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}
expected=$(sed -n 's/^__version__ = "\([0-9.]*\)"$/\1/p' "$plugin_root/src/knowledge_refinery/__init__.py")
if [ -z "$expected" ]; then
    echo "Knowledge Refinery Plugin のバージョンを読み取れません。" >&2
    exit 1
fi

if ! command -v knowledge-refinery >/dev/null 2>&1; then
    message="PATH に knowledge-refinery が見つかりません。CLI $expected を導入し、ホストの PATH を確認してください。"
elif ! actual=$(knowledge-refinery --version </dev/null 2>/dev/null); then
    message="knowledge-refinery --version が失敗しました。CLI $expected のインストール状態を確認してください。"
elif [ "$actual" = "$expected" ]; then
    exec knowledge-refinery context guidance-hook
else
    case "$actual" in
        ''|*[!a-zA-Z0-9.+_-]*) actual='取得不能' ;;
    esac
    message="Knowledge Refinery のバージョンが異なります（Plugin $expected、CLI $actual）。CLI を Plugin と同じ版に揃えてください。"
fi

printf '{"systemMessage":"%s"}\n' "$message"
