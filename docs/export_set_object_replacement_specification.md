# Export Sets オブジェクト置換仕様

## 状態

- この文書は実装前の方針整理です。
- 対象は `EXPORT_SETS` 専用です。
- 目的は、Export Set に含まれる特定オブジェクトを別オブジェクトへ置換して書き出せるようにすることです。

---

## 目的

- Export Set の一部オブジェクトだけを、元シーンを変更せずに別オブジェクトへ差し替えて export できるようにします。
- mesh 本体だけでなく、armature modifier などの安全に追従できる参照も置換後へ合わせます。
- 置換によって壊れる可能性が高い modifier は黙って書き出さず、検出してその Export Set をエラー停止します。

---

## 対象範囲

- 今回の実装対象は `batch_mode = EXPORT_SETS` のみです。
- `OFF` `SCENE` `COLLECTION` `SCENE_COLLECTION` `ACTIVE_SCENE_COLLECTION` `OBJECTS_IN_ACTIVE_COLLECTION` には入れません。

---

## 既存責務の維持

- `func_export_sets.build_export_set_runtime()` を、`EXPORT_SETS` の書き出し用複製を作る唯一の入口として維持します。
- `func_export_sets.cleanup_runtime()` を、複製破棄と名前復元の出口として維持します。
- `EXPORT_SETS` 経路に追加の複製層は作りません。
- 名前入れ替えは既存どおり `func_temporary_duplicate_names` を使う前提で進めます。

---

## 追加する設定

### Export Set 単位

- オブジェクト置換ルール一覧を追加します。

### 置換ルール単位

- `enabled`
- `source_object`
- `replacement_object`
- `include_children`

`include_children` は、置換元 root 配下をまとめて置換するか、単体だけ置換するかを表します。

---

## 基本動作

- 置換は export 前の対象解決段階で適用します。
- いったん複製した後に source 複製を replacement 複製へ入れ替えるのではなく、最初から「何を複製するか」を置換後の集合として確定します。
- armature 推論も、置換前ではなく置換後の実効対象集合に対して行います。

---

## 実行順

1. Export Set item ごとに root と children を解決します。
2. その item に含まれるオブジェクト集合へ置換ルールを適用します。
3. 置換後の実効対象集合から、複製対象オブジェクトを確定します。
4. `build_export_set_runtime()` がその集合だけを複製します。
5. 複製後に、安全な参照だけを置換後複製へ張り替えます。
6. その後に既存の `merge_armatures()` `join_runtime_meshes()` `apply_runtime_vertex_color_replace_rules()` などの後段処理を流します。

---

## 参照置換の方針

- modifier 内の Object 参照を一括で総置換してはいけません。
- 自動置換は whitelist 方式にします。
- 初期対応で自動置換するのは次だけに限定します。
  - `object.parent`
  - `parent_type == 'BONE'` と `parent_bone`
  - `ARMATURE` modifier の `modifier.object`

---

## 自動置換しない参照

- 事前バインドや内部キャッシュに依存する参照は、自動では置換しません。
- 少なくとも次は危険側として扱います。
  - `Surface Deform`
  - `Mesh Deform`
  - `Hook`
- 同種の「参照先変更だけでは元の意味を維持できない modifier」は同じ扱いにします。

---

## 危険な参照の扱い

- 置換元を参照している危険な modifier が export 対象内に残っていた場合、その Export Set はエラー停止します。
- 壊れる可能性がある参照を黙って残したまま export してはいけません。
- エラーには少なくとも次を含めます。
  - オブジェクト名
  - modifier 名
  - 参照プロパティ名
  - 参照先オブジェクト名

---

## 不変条件

- 元の blend データへ置換結果を残さないこと。
- `EXPORT_SETS` で複製生成責務を増やさないこと。
- 安全に直せる参照だけを自動で直すこと。
- 安全に直せない参照は検出して停止すること。
- 置換後の object 解決、armature 推論、merge、join が同じ runtime 上で完結すること。

---

## 未確定事項

- 置換後の FBX 上の object 名と armature 名を、置換元名に寄せるか、置換先名のまま出すかは未確定です。
- ここは後段の既存運用への影響を見て決めます。

---

## 実装の分担

- `props_export_sets.py`
  - 置換ルール PropertyGroup を追加
  - Export Set へルール一覧と active index を追加

- `panel_export_sets.py`
  - Export Set 編集 UI に置換ルール一覧と詳細編集 UI を追加

- `ops_export_sets.py`
  - 置換ルールの追加、削除、複製、並べ替え
  - Export Set 複製時のルール複製

- `func_export_sets.py`
  - item ごとの実効対象解決へ置換ルール適用を追加
  - 置換後集合ベースの armature 推論へ変更
  - 安全な参照の retarget 処理を追加
  - 危険な参照の検出とエラー化を追加

---

## テスト方針

- runtime 解決テスト
  - item ごとの `duplicate_root` と `duplicate_armature` が置換後実体を指すこと

- scope/export テスト
  - 置換で不要な兄弟 object が混ざらないこと
  - 書き出し後の mesh 名、頂点数、armature 名、bone 親子が期待どおりであること

- armature 参照テスト
  - armature modifier が置換後 armature を指すこと

- 危険参照テスト
  - `Surface Deform` など危険な参照が残る場合に、その Export Set が明示的に失敗すること

- 回帰テスト
  - 既存の `test_export_sets_runtime_mapping.py`
  - 既存の `test_export_sets_scope_export.py`
  - 既存の `test_export_sets_multi_armature_modal_operator.py`
  - 既存の `test_export_sets_vertex_color_modal_operator.py`
  を壊さないこと
