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

from mod_text import collect_and_process_html_files, analyze_consolidate_and_clean_files
from dump2html import SlackJsonToHtml

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
        "--skip-dump",
        action="store_true",
        help="Skip slackdump",
    )
    parser.add_argument(
        "--skip-merge",
        action="store_true",
        help="Skip merging existing backups",
    )
    parser.add_argument(
        "--skip-convert",
        action="store_true",
        help="Skip converting zip to HTML",
    )
    parser.add_argument(
        "--skip-analyze",
        action="store_true",
        help="Skip analyzing and cleaning text files",
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
            "export",
            "-o",
            "slackdump.zip",
            "-type",
            "standard",
            "-files=false",
            "C069K1AS24T",  # _23 1
            "C069YBU03JN",  # _23 2
            "C07FD974XND",  # _24
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




def main():
    args = parse_args()
    Path("html").mkdir(exist_ok=True)
    Path("txt").mkdir(exist_ok=True)

    try:
        if not args.skip_dump:
            token, cookie = get_credentials()
            zip_path = run_slackdump(token, cookie)

        if args.skip_merge:
            _zip_path = Path("./backups/slackdump_20240821_000000.zip")

            if not Path("./slackdump.zip").exists():
                zip_path = Path(shutil.copy2(_zip_path, "./slackdump.zip"))
            else:
                zip_path = Path("./slackdump.zip")
        else:
            zip_path = merge_zip_files()
            if not zip_path:
                print("マージするファイルが見つかりません")
                sys.exit(1)

        if not args.skip_convert:
            print("HTMLファイルに変換中...")
            # subprocess.run(
            #     ["python", "dump2html.py", "-i", str(zip_path), "-o", "./html"],
            #     check=True,
            # )

            # unzip
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall("./slackdump")

            # dump folder nameをすべて取得
            dump_folders = [f.name for f in Path("./slackdump").glob("*") if f.is_dir()]
            SlackJsonToHtml(Path("./slackdump"), "./html", dump_folders)

        print("テキストファイルを生成中...")
                # メイン処理
        folder_path = "./html"
        output_folder = "./txt"

        collect_and_process_html_files(folder_path, output_folder)

        if not args.skip_analyze:
            analyze_consolidate_and_clean_files(output_folder)

        print("\n処理が完了しました")
        print("./txtディレクトリに47個のテキストファイルが生成されています")
        print("これらのファイルをNotebookLMにアップロードしてください")

    except subprocess.CalledProcessError as e:
        print(f"エラーが発生しました: {e}")
        sys.exit(1)

    # htmlディレクトリを削除
    # shutil.rmtree("html")


if __name__ == "__main__":
    main()
