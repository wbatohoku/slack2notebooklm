from pathlib import Path
from typing import List, Tuple
from math import ceil
import re
from io import StringIO


class FilePartitioner:
    """ファイル分割・結合を管理するクラス"""

    def __init__(
        self,
        max_size: int,
        max_files: int,
        output_dir: Path,
        split_pattern: str = r"\n\s*\n",
        join_pattern: str = "\n\n",
        encoding: str = "utf-8",
    ):
        """
        Args:
            max_size: 出力ファイルの最大サイズ（バイト）
            max_files: 出力ファイルの最大数
            output_dir: 出力ディレクトリのパス
            split_pattern: 分割に使用する正規表現パターン
            join_pattern: ファイル結合時の区切りパターン
            encoding: ファイルのエンコーディング
        """
        self.max_size = max_size
        self.max_files = max_files
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.split_pattern = re.compile(split_pattern)
        self.join_pattern = join_pattern
        self.encoding = encoding
        # 結合パターンのサイズを計算
        self.join_pattern_size = len(join_pattern.encode(encoding))

    def count_characters(self, text: str) -> int:
        """文字列のバイトサイズを計算"""
        return len(text)

    def split_text_by_pattern(self, text: str) -> List[str]:
        """テキストを正規表現パターンで分割"""
        blocks = [
            block.strip() for block in self.split_pattern.split(text) if block.strip()
        ]
        return blocks

    def split_file(self, input_path: Path) -> List[Path]:
        """大きいファイルを分割"""
        output_paths = []
        part_number = 1

        with input_path.open("r", encoding=self.encoding) as f:
            content = f.read()

        blocks = self.split_text_by_pattern(content)
        current_part = StringIO()
        current_size = 0

        for block in blocks:
            block_size = self.count_characters(block)

            if block_size > self.max_size:
                # 現在のパートを保存
                if current_size > 0:
                    output_path = self._save_part(current_part, input_path, part_number)
                    output_paths.append(output_path)
                    current_part = StringIO()
                    current_size = 0
                    part_number += 1

                # 大きいブロックを行単位で分割
                lines = block.splitlines(True)
                for line in lines:
                    line_size = self.count_characters(line)
                    if current_size + line_size > self.max_size:
                        if current_size > 0:
                            output_path = self._save_part(
                                current_part, input_path, part_number
                            )
                            output_paths.append(output_path)
                            current_part = StringIO()
                            current_size = 0
                            part_number += 1
                    current_part.write(line)
                    current_size += line_size

            elif current_size + block_size + self.join_pattern_size > self.max_size:
                output_path = self._save_part(current_part, input_path, part_number)
                output_paths.append(output_path)
                current_part = StringIO()
                current_part.write(block + self.join_pattern)
                current_size = block_size + self.join_pattern_size
                part_number += 1
            else:
                current_part.write(block + self.join_pattern)
                current_size += block_size + self.join_pattern_size

        if current_size > 0:
            output_path = self._save_part(current_part, input_path, part_number)
            output_paths.append(output_path)

        input_path.unlink()

        return output_paths

    def _save_part(
        self, current_part: StringIO, input_path: Path, part_number: int
    ) -> Path:
        """パートをファイルとして保存"""
        content = current_part.getvalue().rstrip()
        output_path = (
            self.output_dir / f"{input_path.stem}_part{part_number}{input_path.suffix}"
        )

        with output_path.open("w", encoding=self.encoding) as out_f:
            out_f.write(content)

        return output_path

    def concatenate_files(self, files: List[Path], output_name: str) -> Path:
        """小さいファイルを結合"""
        output_path = self.output_dir / f"{output_name}.txt"
        total_content = StringIO()
        first_file = True

        for file_path in files:
            with file_path.open("r", encoding=self.encoding) as in_f:
                content = in_f.read()
                if not first_file:
                    total_content.write(self.join_pattern)
                total_content.write(content)
                first_file = False
            file_path.unlink()

        content = total_content.getvalue()
        with output_path.open("w", encoding=self.encoding) as out_f:
            out_f.write(content)

        return output_path

    def get_file_size(self, path: Path) -> int:
        """ファイルのサイズを取得"""
        with path.open("r", encoding=self.encoding) as f:
            return self.count_characters(f.read())

    def is_feasible(self, files: List[Path]) -> bool:
        """問題が実現可能かどうかを判定"""
        large_files_parts = 0
        small_files_size = 0

        for file_path in files:
            size = self.get_file_size(file_path)

            if size > self.max_size:
                with file_path.open("r", encoding=self.encoding) as f:
                    content = f.read()
                blocks = self.split_text_by_pattern(content)
                current_size = 0
                parts_needed = 1

                for block in blocks:
                    block_size = self.count_characters(block)
                    if block_size > self.max_size:
                        parts_needed += ceil(block_size / self.max_size)
                        continue

                    if (
                        current_size + block_size + self.join_pattern_size
                        > self.max_size
                    ):
                        parts_needed += 1
                        current_size = block_size + self.join_pattern_size
                    else:
                        current_size += block_size + self.join_pattern_size

                large_files_parts += parts_needed
            else:
                small_files_size += size

        min_bins_small = ceil(small_files_size / self.max_size)
        total_min_files = large_files_parts + min_bins_small

        return total_min_files <= self.max_files

    def process_files(self, input_files: List[Path]) -> List[Path]:
        """メインの処理ロジック"""
        if not self.is_feasible(input_files):
            raise ValueError(
                "Given constraints cannot be satisfied with these input files"
            )

        output_files = []
        small_files = []

        # ファイルを文字数で分類し、大きいファイルを処理
        for file_path in input_files:
            size = self.get_file_size(file_path)
            if size > self.max_size:
                split_files = self.split_file(file_path)
                output_files.extend(split_files)
            else:
                small_files.append((size, file_path))

        delete_count = len(small_files) + len(output_files) - self.max_files 
        print("delete_count", delete_count)

        # 小さいファイルのビンパッキング
        if small_files:
            small_files.sort()  # 文字数順でソート
            bins = []  # (current_size, [files])
            file_index = 0

            for size, file_path in small_files:
                file_index += 1
                bin_found = False
                for i, (bin_size, bin_files) in enumerate(bins):
                    if (
                        bin_size + size + (self.join_pattern_size if bin_files else 0)
                        <= self.max_size
                    ):
                        new_size = (
                            bin_size
                            + size
                            + (self.join_pattern_size if bin_files else 0)
                        )
                        bins[i] = (new_size, bin_files + [file_path])
                        bin_found = True
                        break

                if bin_found:
                    delete_count -= 1
                    print("delete_count", delete_count)
                else:
                    bins.append((size, [file_path]))

                if delete_count == 0:
                    break

            output_files.extend([s for _, s in small_files[file_index:]])

            # 各ビンのファイルを結合
            for i, (_, bin_files) in enumerate(bins, 1):
                output_path = self.concatenate_files(bin_files, f"concatenated_{i}")
                output_files.append(output_path)

        if len(output_files) > self.max_files:
            raise RuntimeError(f"Algorithm error: produced more files than allowed: {len(output_files)}")

        return output_files


def main():
    # 使用例
    input_dir = Path("./test_text")
    output_dir = Path("./test_text/test_text_out")

    max_size = 100 * 1024  # 100KB
    max_files = 10

    partitioner = FilePartitioner(
        max_size=max_size,
        max_files=max_files,
        output_dir=output_dir,
        split_pattern=r"\n\s*\n",  # 空行で分割
        join_pattern="\n\n",  # 2行の改行で結合
        encoding="utf-8",
    )

    input_files = list(input_dir.glob("*.txt"))

    try:
        output_files = partitioner.process_files(input_files)
        print(f"Successfully processed files. Output files: {len(output_files)}")
        for f in output_files:
            print(f"- {f.name}: {partitioner.get_file_size(f) / 1024:.2f} KB")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
