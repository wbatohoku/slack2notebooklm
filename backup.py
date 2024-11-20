import os
import subprocess
import sys
import shutil
from pathlib import Path
from datetime import datetime
import zipfile
import tempfile
import argparse
from tqdm import tqdm

def get_credentials():
    print("Slackトークンとクッキーを入力してください")
    token = input("SLACK_TOKEN (xoxcから始まる文字列): ")
    cookie = input("COOKIE (xoxdから始まる文字列): ")

    if not token.startswith("xoxc-") or not cookie.startswith("xoxd-"):
        print("無効なトークンまたはクッキーです")
        sys.exit(1)

    return token, cookie


def get_timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_backup_path():
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    return backup_dir


def archive_with_timestamp(src_zip):
    timestamp = get_timestamp()
    backup_path = get_backup_path()
    new_name = f"slackdump_{timestamp}.zip"
    dst_path = backup_path / new_name
    shutil.copy2(src_zip, dst_path)
    return dst_path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--merge-only",
        action="store_true",
        help="Skip slackdump and only merge existing backups",
    )
    return parser.parse_args()


def merge_zip_files():
    backup_path = get_backup_path()
    zip_files = sorted(backup_path.glob("slackdump_*.zip"), reverse=True)

    if not zip_files:
        return None

    print("既存のバックアップをマージ中...")
    merged_dir = Path(tempfile.mkdtemp())
    conflict_count = {}

    # Add progress bar for zip files
    for zip_path in tqdm(zip_files, desc="ZIPファイル処理"):
        with zipfile.ZipFile(zip_path) as zf:
            members = zf.namelist()
            # Add progress bar for files within each zip
            for member in tqdm(members, desc=f"{zip_path.name} 展開", leave=False):
                target_path = merged_dir / member

                if target_path.exists():
                    base, ext = os.path.splitext(member)
                    while target_path.exists():
                        count = conflict_count.get(member, 0) + 1
                        conflict_count[member] = count
                        new_name = f"{base}_{count}{ext}"
                        target_path = merged_dir / new_name

                zf.extract(member, merged_dir)

    print("マージしたファイルを圧縮中...")
    merged_zip = backup_path / f"merged_{get_timestamp()}.zip"
    with zipfile.ZipFile(merged_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        files_to_zip = []
        for root, _, files in os.walk(merged_dir):
            for file in files:
                files_to_zip.append(
                    (Path(root) / file, str(Path(root).relative_to(merged_dir) / file))
                )

        for file_path, arc_name in tqdm(files_to_zip, desc="圧縮"):
            zf.write(file_path, arc_name)

    shutil.rmtree(merged_dir)
    return merged_zip


def run_slackdump(token, cookie):
    os.environ["SLACK_TOKEN"] = token
    os.environ["COOKIE"] = cookie

    print("Slackデータをエクスポート中...")
    subprocess.run(
        [
            "slackdump",
            "-export",
            "slackdump.zip",
            "-export-type",
            "standard",
        ],
        check=True,
    )

    # Archive the new dump
    archived_path = archive_with_timestamp("slackdump.zip")
    print(f"バックアップを保存しました: {archived_path}")

    # Merge all existing dumps
    merged_path = merge_zip_files()
    if merged_path:
        print(f"マージされたファイルを作成しました: {merged_path}")
        return merged_path
    return archived_path


def process_data(zip_path):
    print("HTMLファイルに変換中...")
    subprocess.run(
        ["python", "./slack2html/slack2html.py", "-z", str(zip_path), "-o", "./html"],
        check=True,
    )

    print("テキストファイルを生成中...")
    subprocess.run(["python", "analyzer.py"], check=True)


def main():
    args = parse_args()
    Path("html").mkdir(exist_ok=True)
    Path("txt").mkdir(exist_ok=True)

    try:
        if args.merge_only:
            zip_path = get_backup_path()
            if not zip_path:
                print("マージ可能なバックアップが見つかりません")
                return
        else:
            token, cookie = get_credentials()
            zip_path = run_slackdump(token, cookie)

        merge_zip_files()

        process_data(zip_path)

        print("\n処理が完了しました")
        print("./txtディレクトリに47個のテキストファイルが生成されています")
        print("これらのファイルをNotebookLMにアップロードしてください")

    except subprocess.CalledProcessError as e:
        print(f"エラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
