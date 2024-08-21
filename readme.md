# Slack Data Processing for NotebookLM

[NotebookLMはこちら](https://notebooklm.google.com/notebook/5b7f2979-468a-430b-9089-92a5feaf2da3)

SlackのデータをNotebookLMにアップロードするための前処理を行うスクリプトです。

チャンネルごとにテキストファイルを生成します。

ただし、NotebookLMの最大ファイル数は49だそうなので、テキスト量が上位47のチャンネルのみ残し、残りのチャンネル（削除・アーカイブ済み含む）はothers.txtに集約します。

# setup

```bash
conda create -p ./.conda --file requirements.txt
conda activate ./.conda
git clone https://github.com/hfaran/slack2html
python ./slack2html/slack2html.py -z <ZIPFILE_PATH> -o ./html
python ./analyzer.py
```

上記を実行すると、`./txt`に47個のテキストファイルが作成されているはずです。これらのファイルをNotebookLMにアップロードしてください。

# Note

Windowsでは、`python ./slack2html/slack2html.py -z <ZIPFILE_PATH> -o ./html`の実行時に文字化けが発生します。

その場合は `.conda\Lib\site-packages\slackviewer\archive.py` 70行目


```python
        with zipfile.ZipFile(filepath) as zip:
```
を

```python
        with zipfile.ZipFile(filepath, metadata_encoding="utf-8") as zip:
```

に変更してください。