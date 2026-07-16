# refinery-memory

複数のexperienceから繰り返し使える判断原則を抽出します。project固有memoryとcross-projectなshared memoryを使い分け、根拠experience IDを必須とします。shared memoryは `project-id/experience-id` 形式の実在する根拠を2 project以上から指定し、全根拠を本文取得してから作成します。既存memoryの更新は直前に読んだ `updated_at` を要求し、競合上書きを拒否します。
