# Slack Data Processing for NotebookLM

[NotebookLMはこちら](https://notebooklm.google.com/notebook/5b7f2979-468a-430b-9089-92a5feaf2da3)

SlackのデータをNotebookLMにアップロードするための前処理を行うスクリプトです。

チャンネルごとにテキストファイルを生成します。

ただし、NotebookLMの最大ファイル数は49だそうなので、テキスト量が上位47のチャンネルのみ残し、残りのチャンネル（削除・アーカイブ済み含む）はothers.txtに集約します。

# setup

環境構築にはcondaを使用します。

```bash
conda create -p ./.conda --file requirements.txt
git clone https://github.com/hfaran/slack2html
```

Slackのデータをダウンロードするには、[slackdump](https://github.com/rusq/slackdump)を使用します。
事前にインストールし、パスを通しておいてください。

また、Slackのデータをダウンロードする際には、トークンとクッキーが必要です。
どちらもブラウザのデベロッパーツールから取得できます。

トークンの取得: ブラウザでSlackにログインし、デベロッパーツールを開いて以下のコマンドを実行します。

```javascript
JSON.parse(localStorage.localConfig_v2).teams[document.location.pathname.match(/^\/client\/(T[A-Z0-9]+)/)[1]].token
```

これにより、xoxcから始まるトークンが得られます。

クッキーの取得: ストレージからdという名前のクッキーを取得します。これはxoxdから始まります。



# Usage

```bash
conda activate ./.conda
python backup.py
```

上記を実行すると、`./txt`に47個のテキストファイルが作成されているはずです。これらのファイルをNotebookLMにアップロードしてください。

# Note

（少なくとも）Windowsでは、`python ./slack2html/slack2html.py -z <ZIPFILE_PATH> -o ./html`の実行時に文字化け、またはUnicodeEncodeErrorが発生します。

その場合は `.conda\Lib\site-packages\slackviewer\archive.py` 69行目以降の


```python
        # Extract zip
        with zipfile.ZipFile(filepath) as zip:
            print("{} extracting to {}...".format(filepath, extracted_path))
            for info in zip.infolist():
                print(info.filename)
                info.filename = info.filename.encode("cp437").decode("utf-8")
                print(info.filename)
                zip.extract(info,path=extracted_path)
```
を

```python
        # Extract zip
        # with zipfile.ZipFile(filepath) as zip:
        with zipfile.ZipFile(filepath, metadata_encoding="utf-8") as zip:
            print("{} extracting to {}...".format(filepath, extracted_path))
            for info in zip.infolist():
                print(info.filename)
                # info.filename = info.filename.encode("cp437").decode("utf-8")
                print(info.filename)
                zip.extract(info,path=extracted_path)
```

に変更してください。