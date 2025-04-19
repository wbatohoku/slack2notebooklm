import zipfile
import os
import shutil
from pathlib import Path
import tempfile


def reencode_zip(
    input_zip_path, output_zip_path, input_encoding="cp932", output_encoding="utf-8"
):
    """
    ZIPファイルを解凍し、指定されたエンコーディングで再圧縮します。

    Args:
        input_zip_path (str): 入力ZIPファイルのパス
        output_zip_path (str): 出力ZIPファイルのパス
        input_encoding (str): 入力ZIPファイルのエンコーディング（デフォルト: cp932）
        output_encoding (str): 出力ZIPファイルのエンコーディング（デフォルト: utf-8）
    """
    # 一時ディレクトリの作成
    temp_dir = Path(tempfile.mkdtemp())
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()

    try:
        # 入力ZIPファイルを解凍
        with zipfile.ZipFile(input_zip_path, "r") as zip_ref:
            # ファイル名のエンコーディングを指定して解凍
            for file_info in zip_ref.filelist:
                # ファイル名をデコード
                filename = file_info.filename.encode(input_encoding).decode(output_encoding)
                if filename.endswith("/"):
                    # ディレクトリの場合はスキップ
                    continue
                # 解凍先のパスを作成
                extract_path = temp_dir / filename
                # 必要なディレクトリを作成
                extract_path.parent.mkdir(parents=True, exist_ok=True)

                # ファイルを解凍
                with zip_ref.open(file_info) as source, open(
                    extract_path, "wb"
                ) as target:
                    shutil.copyfileobj(source, target)

        # 新しいZIPファイルを作成
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zip_ref:
            # 全てのファイルを再圧縮
            for file_path in temp_dir.rglob("*"):
                if file_path.is_file():
                    # 相対パスを計算
                    arcname = str(file_path.relative_to(temp_dir))
                    # 新しいエンコーディングでファイル名を設定
                    arcname = arcname
                    # ファイルを圧縮
                    zip_ref.write(file_path, arcname)

    finally:
        # 一時ディレクトリの削除
        shutil.rmtree(temp_dir)


def main():
    # 使用例
    input_zip = "./backups/slackdump_20240821_000000.zip"  # 入力ZIPファイル
    output_zip = "output.zip"  # 出力ZIPファイル

    # Windows環境で作成されたZIPファイルをUTF-8に変換する例
    reencode_zip(
        input_zip,
        output_zip,
        input_encoding="cp437",  # Windowsの日本語環境でよく使用される
        output_encoding="utf-8",  # 出力をUTF-8に
    )


if __name__ == "__main__":
    main()
