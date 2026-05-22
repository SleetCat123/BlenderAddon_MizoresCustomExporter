# FBXエクスポート用 Scale 挙動変更仕様

## 状態

- この文書は実装前の仕様整理です。
- 対象は `scripts/custom_exporter_fbx` の既存 `Scale` 挙動の置き換えです。

---

## 背景

- 現在の `Scale` は、出力サイズを拡大すると exported object の `scale` 数値も同じ倍率で大きくなります。
- そのため、たとえば 50 倍で出力した場合に Unity などで `scale = 50` のような値が残り、扱いづらくなります。
- 今回の目的は、見た目の出力結果は通常の拡大と同じまま、必要に応じて exported object の `scale` 数値だけを拡大前の値へ維持できるようにすることです。

---

## 変更対象

- 既存の `Scale` 数値欄は残します。
- `Scale` の効かせ方を選ぶ新しい設定を追加します。
- `Scale` の基準点を選ぶ新しい設定を追加します。

---

## 追加する設定

### 1. Scale Value Mode

- `通常`
  - 現在の `Scale` と同じ動作です。
  - 出力サイズも exported object の `scale` 数値も倍率に応じて変わります。

- `scale値を維持`
  - 出力サイズ、位置、親子関係の見え方、アニメーション結果は `通常` と同一にします。
  - ただし exported object の `scale` 数値だけは拡大前の値を維持します。

### 2. Scale Pivot

- `World Origin`
  - ワールド原点基準で拡縮します。
  - 原点からの距離も含めて変化します。

- `Each Object Origin`
  - 各オブジェクト原点基準で拡縮します。
  - 各オブジェクトの原点位置は維持し、見た目サイズだけ変えます。

---

## 基本動作

- `Scale` の倍率は引き続きユーザー入力値を使います。
- `Scale Value Mode = 通常` では、現在の `global_scale` と同等の結果を維持します。
- `Scale Value Mode = scale値を維持` では、`World Origin` と `Each Object Origin` で処理経路を分けます。
  - `World Origin`
    - FBX exporter の `FBX_SCALE_ALL` 相当で書き出し、FBX 側の global scale へ倍率を載せます。
  - `Each Object Origin`
    - 通常拡大と同じ見た目になるようにエクスポート用複製データ側へ倍率を事前反映し、FBX 側へ不要な `scale` 数値を残しません。
- `Scale Pivot` は `通常` と `scale値を維持` の両方で効きます。

---

## 不変条件

- 同じ `Scale` 値なら、`通常` と `scale値を維持` で見た目の出力結果は一致すること。
- `scale値を維持` で変わってよいのは、exported object の `scale` 数値だけであること。
- 元の blend 内オブジェクトの `scale`、位置、親子関係、アニメーションデータはエクスポート後に変化しないこと。
- 完了、キャンセル、エラーのどの場合でも元シーンへ変更を残さないこと。

---

## 具体例

- 元のオブジェクト `scale = 1.5`
- エクスポート設定 `Scale = 2.0`

### `Scale Value Mode = 通常`

- 出力サイズは `1.5 × 2.0` 相当
- exported object の `scale` 数値も 2 倍側へ変化

### `Scale Value Mode = scale値を維持`

- 出力サイズは `1.5 × 2.0` 相当
- exported object の `scale` 数値は `1.5` を維持

---

## Pivot ごとの挙動

### `World Origin`

- 見た目サイズが変わるだけでなく、原点からの距離も倍率に応じて変化します。
- 複数オブジェクトをまとめて拡大したとき、全体配置も原点基準で広がります。

### `Each Object Origin`

- 各オブジェクトはその場で拡大・縮小します。
- オブジェクト原点の位置は維持します。
- 親子階層がある場合も、通常拡大時と同じ見た目を保つように複製側の transform を調整します。

---

## アニメーション対応

- `bake_anim` 使用時も `scale値を維持` に対応させます。
- 目標は、`通常` と `scale値を維持` でアニメーション再生結果が一致することです。
- 対象には少なくとも以下を含めます。
  - Armature を含む FBX
  - ボーン階層
  - 位置系キーフレーム
  - エクスポート時に生成される AnimStack / Action ベースのアニメーション名

---

## アニメーション名と一時複製の扱い

- 実装では複製オブジェクト、複製アーマチュア、複製アクションを使う可能性があります。
- その場合でも、FBX に書き出されるアニメーション名は現在の名前から変わらないことを必須条件にします。
- 一時複製によって `Action.001` などの名前へ変わる場合は、エクスポート直前に必要な一時リネームを行い、エクスポート後に必ず復元します。
- 復元対象には少なくとも以下を含めます。
  - オブジェクト名
  - データブロック名
  - Action 名
  - NLA / AnimStack の元になる名称

---

## 適用範囲

- `OFF`
- `SCENE`
- `COLLECTION`
- `SCENE_COLLECTION`
- `ACTIVE_SCENE_COLLECTION`
- `OBJECTS_IN_ACTIVE_COLLECTION`
- `EXPORT_SETS`

すべて同じ規則で扱います。

---

## 保存互換

- 新しい設定は既存の export 設定保存と同じく blend 内へ保存します。
- 既存 blend を開いたときの既定動作は、現在の挙動から変えないため `Scale Value Mode = 通常` を既定値にします。
- `Scale Pivot` の既定値は、現在の拡大感覚に近い方を実装時に明示します。現時点では `World Origin` 想定です。

---

## 実装方針メモ

- 元シーンを直接変更せず、既存のエクスポート経路がすでに持っている一時データ層へ処理を載せます。
- 既存の undo 復元に依存するだけでなく、一時的に変更した名前や参照も必ず個別に戻せる構成にします。
- `scale値を維持` では、`World Origin` は FBX の global scale を使い、`Each Object Origin` は複製側 transform / データ / 必要なアニメーション値へ倍率を反映します。

### 複製責務の不変条件

- `EXPORT_SETS` では `func_export_sets.build_export_set_runtime()` が書き出し用複製の唯一の生成地点です。
- `Scale Value Mode` の実装は、`EXPORT_SETS` で追加の複製層を作ってはいけません。
- `OFF` `SCENE` `COLLECTION` `SCENE_COLLECTION` `ACTIVE_SCENE_COLLECTION` `OBJECTS_IN_ACTIVE_COLLECTION` は export set runtime を持たないため、必要な一時データはその経路にだけ追加します。
- 実装前に「対象が元オブジェクトか、既存の一時複製か」を batch mode ごとに確定しないまま共通化してはいけません。

---

## テスト観点

- 設定保存
  - `Scale Value Mode`
  - `Scale Pivot`
- 出力結果
  - `通常` と `scale値を維持` で見た目が一致すること
  - `World Origin` と `Each Object Origin` で位置変化規則が意図どおり異なること
- 復元
  - エクスポート後に元シーンの `scale` が変わっていないこと
  - 一時変更した名前がすべて戻ること
- アニメーション
  - `bake_anim` 有効時も見た目結果が一致すること
  - アニメーション名が変わらないこと
