
## 更新履歴
### 2025-xx v1.2.0
  - add: エクスポート時のシェイプキーベース形状変更機能を追加（ShapeKeysUtil連携）
  - add: エクスポート時のシェイプキー並び替え機能を追加（ShapeKeysUtil連携）
  - add: Export Sets機能を追加（名前付きエクスポートセットを定義して一括出力）
    - セット単位でオブジェクト置換ルール（Object Replace）を設定可能
    - セット単位で頂点カラー置換ルール（Vertex Color Replace）を設定可能
    - セット単位でアーマチュアマージ（Merge Into One Armature）を設定可能
    - セット単位でメッシュ結合（Join Meshes To One）を設定可能
    - セット単位でシェイプキー並び替えオーバーライドを設定可能
  - add: バッチモードにCollections in Active Collection / Objects in Active Collection / Export Setsを追加
  - add: バッチファイル名フォーマット設定を追加（{name} / {batch}プレースホルダー対応）
  - add: Scale Value Mode（Keep Scale Value）を追加（スケール倍率をデータに焼き付けてFBXスケール値を変えない）
  - add: Scale Pivotオプションを追加（World Origin / Each Object Origin）
  - add: モディファイアタイプフィルターを追加（適用するモディファイアタイプをカテゴリ別に選択可能）
  - add: Fix Vertex Group Name Collisions（頂点グループ名衝突修復）を追加
  - add: Limit Vertex Weight Count（頂点ウェイト数上限）を追加
  - add: エクスポート時にシェイプキーを全て削除するプロパティ（ClearAllShapekeysWhenExport）を追加
  - add: エクスポート時にシェイプキーを全て適用するプロパティ（ApplyAllShapekeysWhenExport）を追加
  - add: Use Bone Constraintオプションを追加（アニメーションベイク時のボーンコンストレイント適用）
  - change: エクスポート処理をModal対応に変更（ESCキーでキャンセル可能）
  - add: エクスポート中の進捗表示を追加（GPUプログレスバー）
  - add: エクスポート完了後の結果ダイアログを追加（出力ファイル数・サイズ・処理時間）

### 2024-11- v1.1.0
  - add: 複数のUVタイルを1つのタイルにしてエクスポートするグループを追加（[0,0]-[1,1]の範囲に収まるようにUV頂点を移動する）
  - add: ShapeKeysUtilのベースシェイプキー減算機能をエクスポート前処理に追加
  - change: Smoothingのエクスポート設定のデフォルト値をFaceに変更
  - fix: prop割り当てパネルでInclude Childrenが機能していなかったのを修正

### 2024-10-18 v1.0.1
  - change: エクスポート対象オブジェクトタイプのデフォルト値を{Armature, Mesh}から{Armature, Mesh, Other}に変更
  - fix: オブジェクトモード以外でエクスポートしようとするとエラーが出る場合があるのを修正
  
### 2024-09-03 v1.0.0
  - 公開
  - アドオン連携の互換性: 
    - [AutoMerge](https://github.com/SleetCat123/BlenderAddon-AutoMerge): 3.0.0-
    - [ShapeKeysUtil](https://github.com/SleetCat123/BlenderAddon_ShapeKeysUtil): 2.0.0-
