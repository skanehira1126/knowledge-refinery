# refinery-propose-improvements

1件または複数の解析レポートから、Skill化・CLI化／既存CLI拡張・AGENTS.mdへの反映・
既存機能の再利用や改善・見送りを比較する明示呼び出し専用Skillです。

```text
$knowledge-refinery:refinery-propose-improvements を使い、reports/session-review.md から
優先する改善案と具体的な変更案を提案してください。
```

作業IDと根拠位置を使って候補を比較し、同じ履歴の転載や再試行を独立需要に数えません。
AGENTS.md案は適用先と短い文案、CLI案は入出力・エラー・副作用、Skill案は発火条件と判断箇所を示します。
同等規則が既存AGENTS.mdにある場合は重複追記せず、矛盾・配置・到達性・遵守を検討します。

旧形式のレポートも不足を明示して使えます。利用可能なexperience/memoryは既存のアクセス条件で検索し、
未設定・無効・接続不可ならレポートだけで続けます。知見保存や新しい設定を前提にしません。
指定先がなければ `improvement-proposals.md` に保存し、元レポートと既存ファイルを保持します。
提案から実装・インストールへ自動で進みません。
