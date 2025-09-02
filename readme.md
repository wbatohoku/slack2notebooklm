# Slack Data Processing for NotebookLM

[NotebookLM はこちら](https://notebooklm.google.com/notebook/5b7f2979-468a-430b-9089-92a5feaf2da3)

Slack のデータを NotebookLM にアップロードするための前処理を行うスクリプトです。

チャンネルごとにテキストファイルを生成します。

ただし、NotebookLM の最大ファイル数は 49 だそうなので、テキスト量が上位 47 のチャンネルのみ残し、残りのチャンネル（削除・アーカイブ済み含む）は others.txt に集約します。

# setup

環境構築には conda を使用します。

```bash
conda create -p ./.conda --file requirements.txt
```

Slack のデータをダウンロードするには、[slackdump](https://github.com/rusq/slackdump)を使用します。
事前にインストールし、パスを通しておいてください。

また、Slack のデータをダウンロードする際には、トークンとクッキーが必要です。
どちらもブラウザのデベロッパーツールから取得できます。

トークンの取得: ブラウザで Slack にログインし、デベロッパーツールを開いて以下のコマンドを実行します。

```javascript
JSON.parse(localStorage.localConfig_v2).teams[
  document.location.pathname.match(/^\/client\/(T[A-Z0-9]+)/)[1]
].token;
```

これにより、xoxc から始まるトークンが得られます。

クッキーの取得: ストレージから d という名前のクッキーを取得します。これは xoxd から始まります。

# Usage

```bash
conda activate ./.conda
python backup.py
```

上記を実行すると、`./txt`に 47 個のテキストファイルが作成されているはずです。これらのファイルを NotebookLM にアップロードしてください。

# 複数の Slack ワークスペースでの利用

このツールは、基本的に一つの Slack ワークスペースのデータを継続的に蓄積することを想定していますが、一時的に別のワークスペースのデータを処理することも可能です。

## データの蓄積の仕組み

1. **データの流れ**:

   - Slack から取得したデータは `slackdump.zip` として保存
   - この ZIP ファイルは日時のタイムスタンプを付けて `backups/` ディレクトリにコピーされる
   - 実行のたびに既存のバックアップ ZIP ファイルがマージされ、履歴が蓄積される
   - マージされた ZIP ファイルから HTML が生成され、最終的にテキストファイルが出力される

2. **重要なディレクトリ**:
   - `backups/`: 生データとマージされたデータの保存場所（**最重要**）
   - `html/`: 中間処理データ（一時的なもの）
   - `txt/`: 最終出力データ（一時的なもの）

## 別ワークスペースでの一時利用

別の Slack ワークスペースでこのツールを一時的に使用する場合は、以下の手順を実行してください：

1. **現在のデータのバックアップ**:

   ```bash
   # backupsディレクトリをバックアップ
   cp -r backups backups_original_workspace
   # 必要に応じてtxtもバックアップ
   cp -r txt txt_original_workspace
   ```

2. **新しいワークスペースでの実行**:

   - 新しいワークスペースのトークンとクッキーを取得
   - `backups`ディレクトリを空にするか、名前を変更（例：`backups_temp`）して新規作成
   - 以下のコマンドを実行:

   ```bash
   python backup.py
   ```

3. **元のワークスペースに戻す**:
   - 新しく生成されたデータをバックアップしたい場合は別途保存
   - 元のバックアップを戻す:
   ```bash
   rm -rf backups  # 現在のbackupsを削除
   mv backups_original_workspace backups  # 元のbackupsを戻す
   rm -rf txt html  # 一時的な出力を削除
   python backup.py --skip-dump  # 再処理（ダウンロードをスキップ）
   ```

## バックアップと復元

`backups`ディレクトリには全ての元データが含まれています。`txt`と`html`ディレクトリは一時的な出力先であり、`backups`から常に再生成できます。

**復元手順**:

1. 保存していた`backups`ディレクトリを元の場所に配置
2. 以下のコマンドを実行:
   ```bash
   python backup.py --skip-dump
   ```

## マージ機能について

`backup.py`には`merge_zip_files`関数があり、これが履歴の蓄積を可能にしています：

- 実行時に`backups`ディレクトリ内の全ての zip ファイルをマージ
- マージされた zip ファイルは`merged_{timestamp}.zip`として保存
- マージ時にファイル名の衝突があれば自動的に解決（連番付加）

この機能をスキップするには`--skip-merge`オプションを使用します：

```bash
python backup.py --skip-merge
```
