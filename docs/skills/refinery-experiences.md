# refinery-experiences

`refinery-experiences` は、`shared/stock` から短い経験則を手動で抽出し、`shared/experiences` と `EXPERIENCES.md` の参照範囲を整える skill です。

## 役割

- `shared/stock` の詳細を毎回読まずに済むよう、繰り返し使う判断原則を短く圧縮する
- `EXPERIENCES.md` を参照範囲の index として保つ
- experience ファイルに `source_stock` を残し、根拠 stock へ戻れるようにする
- 古くなった experience や広すぎる experience を棚卸しする

## 使う場面

- stock が増え、通常作業の初期読み込みが重くなってきたとき
- 複数 stock にまたがる実務上の判断基準を安定化したいとき
- タスク別に読むべき experience を `EXPERIENCES.md` で制御したいとき

## 注意

- experience は true memory やモデル学習ではなく、短く圧縮された外部知識として扱う
- `EXPERIENCES.md` は index に徹し、経験則本文は個別ファイルへ分ける
- 新しい事実は直接 experience に入れず、先に `flow` / `review` / `stock` の通常経路で安定化する
