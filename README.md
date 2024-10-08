# MizoresCustomExporter
## ◆概要
- 特定のオブジェクトをエクスポート対象から除外
- 特定のオブジェクトだけは非表示になっているときでも絶対にエクスポートする
- エクスポート時だけモディファイアを適用（同作者の[別アドオン(AutoMerge)](https://github.com/SleetCat123/BlenderAddon-AutoMerge)との連携機能）
- エクスポート時だけオブジェクトを結合（同作者の[別アドオン(AutoMerge)](https://github.com/SleetCat123/BlenderAddon-AutoMerge)との連携機能）
- エクスポート時だけシェイプキーを左右分割（同作者の[別アドオン(ShapeKeysUtil)](https://github.com/SleetCat123/BlenderAddon_ShapeKeysUtil)との連携機能）
といった機能を持ったアドオンです。
現在はfbx形式のエクスポートのみに対応しています。

ダウンロードはこちらから  
https://github.com/SleetCat123/BlenderAddon_MizoresCustomExporter/releases  

## ◆File → Export → Mizores Custom Exporter (.fbx)
オブジェクトをfbxとしてエクスポートします。

エクスポート処理そのものはBlender標準の内部処理を呼び出しているため、
出力フォーマットの差異などは生じないと思われます。

基本的にはBlender標準のfbxエクスポートと同じことができるようになっています。

## ◆Remove Export Settings
`オブジェクトモードの右クリックメニュー → MizoresCustomExporter → Remove Export Settings`  
現在のblendファイルに保存されているMizoresCustomExporterのエクスポート設定を全て削除します。

## ◆Convert Collections
`オブジェクトモードの右クリックメニュー → MizoresCustomExporter → Convert Collections`  
同作者の[AutoMerge](https://github.com/SleetCat123/BlenderAddon-AutoMerge)アドオンの過去バージョン（2.1.0以前）で使用していた制御用コレクションをCustomProperty（新方式）に変換します。

## ◆Object List (Panel)
`サイドメニュー（Nキー）→ Mizore → Object List`  
以下のプロパティの有無を確認したり、プロパティの割り当て／解除を行うことができます。
- AutoMerge
- DontExport
- AlwaysExport

## ◆エクスポートの追加機能
### ◇オブジェクトのプロパティによる特殊処理
各種プロパティは  
`オブジェクトモードの右クリックメニュー > Mizore's Custom Exporter`  
または
`サイドメニュー（Nキー）→Assign (Mizore)`  
から割り当て／解除ができます。

以下のプロパティが割り当てられているオブジェクトはエクスポート時に特殊な処理が行われます。  
エクスポート完了後、全てのオブジェクトは処理前の状態に戻ります。  

- AlwaysExport: このプロパティが有効なオブジェクトは、オブジェクトが非表示になっていてもエクスポートされます。
- DontExport: このプロパティが有効なオブジェクトはエクスポートされません。  
AlwaysExportと同時に有効化した場合はDontExportが優先されます。

- ResetPoseWhenExport: このプロパティが有効なアーマチュアはエクスポート時にポーズがリセットされます。
- ResetShapekeysWhenExport: このプロパティが有効なオブジェクトはエクスポート時にシェイプキーがリセットされます。

- MoveToOriginWhenExport: このプロパティが有効なオブジェクトはエクスポート時に原点に移動します。
- ApplyLocationsWhenExport: このプロパティが有効なオブジェクトはエクスポート時に位置が適用されます。
- ApplyRotationsWhenExport: このプロパティが有効なオブジェクトはエクスポート時に回転が適用されます。
- ApplyScalesWhenExport: このプロパティが有効なオブジェクトはエクスポート時にスケールが適用されます。
- RemoveUnusedGroupsWhenExport: このプロパティが有効なMeshはエクスポート時に未使用のグループが削除されます。
- RemoveGroupsNotBoneNamesWhenExport: このプロパティが有効なMeshはエクスポート時にボーン名以外のグループが削除されます。
- AlwaysResetShapekeys: このプロパティが有効なオブジェクトは、エクスポート対象かどうかに関わらずエクスポート時にシェイプキーが0にリセットされます。  
エクスポート完了後にシェイプキーの状態は復元されます。

**アドオン連携機能 ([AutoMerge](https://github.com/SleetCat123/BlenderAddon-AutoMerge))**  
- MergeGroup: このプロパティが有効なオブジェクトは、エクスポート時に子オブジェクトを結合します。
- DontMergeToParent: このプロパティが有効なオブジェクトは、オブジェクト結合時に親オブジェクトに結合されません。

[AutoMerge](https://github.com/SleetCat123/BlenderAddon-AutoMerge) 2.1.0以前のデータから最新の方式に移行する場合、`Convert Collections` を使用して移行してください。  

## ◇エクスポート対象オブジェクトの設定
### ・Only Root Collections

### ・Selected Objects (Include Children)
通常のSelected Objectsは選択中のオブジェクトしかエクスポートされませんが、この項目を有効にすることで選択中オブジェクトの子階層以下にあるオブジェクトもエクスポートされるようになります。

#### ・Active Collections (Include Children)
通常のActive Collectionsはアクティブなコレクションに属しているオブジェクトしかエクスポートされませんが、この項目を有効にすることでコレクションに属するオブジェクトの子オブジェクトもエクスポートされるようになります。

## ・エクスポート設定
エクスポート設定メニューは標準のfbxエクスポート（io_scene_fbx）を一部改変して使用しています。  

また、一部の初期設定を変更しています。
（このアドオン独自の変更であり、標準のエクスポートの設定には影響しません）

### ・標準のfbxエクスポートと初期設定が異なる項目
- Apply Scalings: デフォルト値をFBX Units Scaleに変更
- Apply Transform: デフォルト値をTrueに変更
- Object Types: デフォルト値を{Armature, Mesh}に変更
- Batch Own Dir: デフォルト値をFalseに変更

### ・設定項目の保存
各種項目の設定状態はblendファイルに保存され、次回以降のエクスポート時に引き継がれます。

アドオン連携機能でオブジェクトの結合などの操作が行われた場合でも、
エクスポート後には処理前の状態が復元されます。
（もしエクスポート後にオブジェクトが増えたり消えたりしていたら不具合です）


## ◆アドオン連携機能

### 同作者の別アドオン AutoMergeとの連携
この連携機能を使うには、[AutoMerge](https://github.com/SleetCat123/BlenderAddon-AutoMerge)を導入する必要があります。

コレクション“MergeGroup”に属するものに対し、
それぞれの子階層以下にあるオブジェクトを結合した上でエクスポートします。

連携機能を有効にすることにより、
```
1. ミラーを付けたまま編集  
2. エクスポートのときだけミラー適用（自動）  
3. シェイプキーを自動で左右分割  
4. エクスポート後は元通り！  
```
ということもできるようになります。


### 同作者の別アドオン ShapeKeysUtilとの連携

この連携機能を使うには、[ShapeKeys Util](https://github.com/SleetCat123/BlenderAddon_ShapeKeysUtil)を導入する必要があります。

連携機能を有効にすることにより、
シェイプキーをもつオブジェクトのモディファイアを適用してエクスポートできます。

※ シェイプキーをもつオブジェクトのモディファイアを適用は“AutoMerge”アドオンの“ShapeKeysUtil”連携機能を介して行われるため、
オブジェクト結合処理が必要ない場合でも“AutoMerge”連携を有効にし、オブジェクトを“MergeGroup”に入れる必要があります。
（モディファイアを適用したいけど子オブジェクトが結合されるのは嫌という場合もありそうなので対応を検討中）

また、エクスポート機能の使用時にシェイプキーの左右分割を行うことができます。
（例：SmileシェイプキーをSmile_leftとSmile_rightという左右別々のシェイプキーに分割）

これにより、
```
1. ミラーを付けたまま編集
2. エクスポートのときだけミラー適用（自動）
3. シェイプキーを自動で左右分割
4. エクスポート後は元通り！
```
ということもできるようになります。

※    
シェイプキーを持つオブジェクトのモディファイア適用処理には時間がかかるため、エクスポート完了までの所要時間が長くなります。


# ◆注意◆

※
マージする際、Armatureを除く全てのモディファイアは適用されます。  
ただし、レンダリング対象でないモディファイア（モディファイア一覧でカメラアイコンが押されていないもの）は適用せず無視されます。  

※
同作者の別アドオン`ShapeKeys Util`との連携機能が無効になっている場合、シェイプキーをもつオブジェクトはモディファイアを無視してマージ処理を行います。  
そのため、意図しない状態のオブジェクトが出力される可能性があります。  

シェイプキーを含まない他のオブジェクトは通常通りにモディファイア適用・マージを行います。  


## ◆不具合・エラーが起きた時
このアドオンの機能はBlender標準のAPIを使って作成しているため、何らかの不具合が発生した場合にはすぐに Undo（Ctrl+Z） すれば機能使用前の状態に復元できます。  
アドオンの機能を使用する直前にデータを保存しておき、不具合が起きた場合はデータを読み込み直すのがより確実です。  

また、以下の連絡先に不具合発生時の状況を送っていただけると修正の手助けになります。  


## ◆連絡先
不具合報告や要望、感想などありましたらこちらにどうぞ。

修正・実装が可能と思われるものに関しては着手を検討しますが、多忙や技術的問題などの理由により対応できない場合があります。  
予めご了承ください。

Twitter：猫柳みぞれ　https://twitter.com/sleetcat123
