# アーキテクチャ

Knowledge Refineryは、利用repo、グローバルPlugin、ローカルMCP、中央vaultを分離します。
プロダクトのsourceとknowledgeの履歴を混ぜず、repo側には接続情報だけを置きます。

```mermaid
flowchart TB
    subgraph Repo["Product repo"]
        RC[".refinery.yaml<br/>project_id + enabled"]
        RL[".refinery.local.yaml<br/>vault_id"]
        AG["AGENTS.md<br/>optional managed guidance"]
    end

    subgraph Plugin["Global Plugin"]
        SK["Plugin Skills"]
        HK["Codex / Claude Code hooks"]
    end

    subgraph Package["PATH上のknowledge-refinery"]
        MCP["local stdio MCP"]
        CLI["context CLI"]
        G["CLIパッケージの運用指示"]
    end

    CFG["User config<br/>active vault"]

    subgraph Vault["Central filesystem vault"]
        PM["projects/&lt;project_id&gt;<br/>metadata / experiences / memory / handoffs"]
        CT["projects/&lt;project_id&gt;/context"]
        SM["shared/memory"]
        KT["knowledge-tags.yaml"]
    end

    AG --> SK
    RC --> MCP
    RL --> MCP
    SK --> MCP
    HK -->|SessionStart| CLI
    RC --> CLI
    CLI -->|guidance-hook| G
    HK -->|mcp_tool| MCP
    MCP -->|本文の配信・更新| CT
    MCP --> CFG
    CFG --> Vault
    MCP --> PM
    MCP --> SM
    MCP --> KT
```

| 要素 | Source of truth | 役割 |
|---|---|---|
| 利用repo | `.refinery.yaml` | project IDと有効状態を共有する |
| ローカルbinding | `.refinery.local.yaml` | repoと個人のvault IDを結び付ける |
| Plugin | SkillsとMCP設定 | Codexの手順とtool interfaceを提供する |
| ユーザー設定 | active vaultのpath | 接続先を選ぶ |
| 中央vault | project/shared knowledge | ナレッジの実体を保存する |

## 境界

- ユーザーが CLI を導入し、各ホストの Plugin が `knowledge-refinery mcp serve` でサーバーを起動します。
- active vaultはユーザー設定に1つ持ちます。設定ファイルは `REFINERY_CONFIG` で明示でき、未指定時は `${XDG_CONFIG_HOME:-$HOME/.config}/knowledge-refinery/config.yaml` を使います。`REFINERY_VAULT` でactive vaultを一時overrideできます。
- repo-scoped MCP toolsは`project_path`を受け、server側で`enabled`、project metadata、repoと
  active vaultの`vault_id`一致を検証します。
- 固定のSessionStart hookは新規開始時・圧縮後にrepoの有効設定を確認し、CLIパッケージ同梱の運用指示を返します。
- project別の可変hookでは、ホストが接続済みの `refinery_deliver_context` に `cwd` と配信先を渡し、
  サーバーがvaultから取得した本文を追加contextにします。本文の更新には現在のrevisionを使います。
  現行のサーバーはクライアントの `cwd` からrepo設定を読みます。別のマシンで動かす場合には、
  その作業ディレクトリをサーバーが参照する仕組みか、projectを別途識別する仕組みが必要です。
  1.0.0の到達条件は、クライアントとサーバーがファイルシステムを共有せずにprojectを識別し、リモートMCP経由でナレッジの参照・更新とhook本文の配信を完結できることです。
  [MCPでの配信・更新](mcp.md#hook-context)・[配信先一覧](cli.md#context)
- 中央vaultを直接開いた明示的な保守では、`refinery_vault_status`で確認した`vault_context`
  を使います。各呼び出しでactive vaultの実パスとIDを照合し、project対象の書き込みでは
  context内の`project_id`も検証します。vault自身のproject登録は不要で、repoのopt-outを
  変更しません。contextは対象識別であり、利用者承認やfilesystem権限の代わりではありません。
- symlinkは人間の閲覧用であり、MCPとCLIの必須依存ではありません。
- vault markerのmanagerとschemaを利用前に検証し、未対応schemaへの書き込みを拒否します。
- 中央vaultの書き込みはatomic replaceとpath lockで破損を防ぎ、project metadata、experience、memory、tag taxonomyの更新は`expected_updated_at`による楽観的排他で競合上書きを拒否します。
- 検索は不正文書を隔離し、exact getは対象IDの正規pathを直接検証します。不正文書の一覧は `refinery_validate` が返します。
- `handoff_ops.py`は引き継ぎのsnapshotとライフタイムを管理します。通常検索に含めず、
  CLI／MCPの専用操作で取得します。詳細は[引き継ぎガイド](handoffs.md)にあります。

## データフロー

1. Skillが `project status` でrepoの有効性を確認する。直接vault保守では `refinery_vault_status` を使う。
2. MCPが `project_path` からproject IDを導出する。保守contextではvault identityと明示対象を検証する。
3. domain処理がproject metadataまたはknowledge文書のYAML schemaとprovenanceを検証する。
4. storage層が中央vaultへatomicに保存する。
5. Git履歴を有効にしたvaultでは、vault Gitがknowledge履歴をproduct Gitとは別に追跡する。

## issue管理

issueはprojectに所有させず、active vault直下の`issues.json`へ独立して保存します。
`projects`には登録済みproject IDを複数紐付けられ、空のままでも作成できます。
`tags`はissue専用の自由な分類で、既存の`knowledge-tags.yaml`とは独立しています。
通常のexperience／memory検索や`refinery_validate`の対象には含めません。
issueコマンドは保存データのschema・ID重複・履歴を読み込み時に検証します。

`issue_ops.py`がドメイン処理と永続化を所有し、`issue_cli.py`がCLIの入力・出力を担当します。
`mcp_server.py` は同じドメイン処理を `refinery_list_issues` と `refinery_get_issue` で公開します。
`refinery-issue` Skillは参照にこの2つのMCP tool、更新やタグ管理にローカルCLIを使います。
ローカルrepoのパスや設定を必要とせず、project IDで紐付けるvault単位の操作です。
そのためrepoの`enabled`はissueの閲覧・更新権限を表しません。

保存形式は`schema_version: 1`と`issues`配列を持つJSONです。既存vaultは移行不要で、
最初の作成時にファイルを生成します。全書き込みを同じプロセス間lockで直列化し、
全体をatomic replaceすることでタグの一括変更も一度に確定します。
各issueは更新ごとに`revision`を増やし、時刻・理由・変更後のfield値を履歴に残します。
古いrevisionによる更新は拒否し、内容が変わらない更新ではrevisionを増やしません。

初期実装はファイル全体を読み書きする小規模なローカル運用向けです。
大量のissueや長い履歴を扱う場合のデータベース化は別途検討します。
