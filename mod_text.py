from pathlib import Path
import re
import matplotlib.pyplot as plt
import japanize_matplotlib

from combine import FilePartitioner

break_line_pattern = r"\n\n\n"

channel_blacklist = [
    "rss_news", 
    "times_shoma_nagata",
    "times_yuki_automated"
]

def clean_html_content(content):
    # スクリプトを削除
    content = re.sub(r"<script>[\s\S]*</script>", "", content)

    # channel-listを削除
    content = re.sub(
        r"<ul class=\"list\" id=\"channel-list\">[\s\S]*</ul>", "", content
    )

    # HTMLタグを削除
    content = re.sub(r"<[^>]+>", "", content)

    # 各行の先頭の空白文字（\n以外）を削除
    content = re.sub(r"^[ \t]+", "", content, flags=re.MULTILINE)

    # 4つ以上連続する空白行を3つの空白行に置換
    content = re.sub("\n{4,}", "\n\n\n", content)

    return content


def collect_and_process_html_files(folder_path, output_folder="./txt", pattern="channel/*/*.html"):
    folder = Path(folder_path)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    processed_files = []

    for file_path in folder.rglob(pattern):
        if any(channel in file_path.parent.name for channel in channel_blacklist):
            continue

        new_filename = f"{file_path.parent.name}.txt"
        new_file_path = output_folder / new_filename

        with file_path.open('r', encoding='utf-8') as f:
            content = f.read()

        print("Processing", new_file_path.name)
        cleaned_content = clean_html_content(content)

        with new_file_path.open('w', encoding='utf-8') as f:
            f.write(cleaned_content)

        processed_files.append((file_path, new_file_path))

    return processed_files


def analyze_consolidate_and_clean_files(output_folder, top_n=47, threshold=100_0000):
    output_dir = Path(output_folder)

    # Initialize FilePartitioner
    partitioner = FilePartitioner(
        max_size=threshold,
        max_files=top_n,
        output_dir=output_dir,
        split_pattern=r"\n\n\n",
        join_pattern="\n\n====================\n\n",
        encoding="utf-8",
    )

    # Get file sizes and paths
    file_sizes: dict[Path, int] = {}
    for file_path in output_dir.glob("*.txt"):
        file_sizes[file_path] = partitioner.get_file_size(file_path)

    # Sort files by size
    sorted_files = sorted(file_sizes.items(), key=lambda x: x[1], reverse=True)
    files_to_process = [f for f, _ in sorted_files]

    try:
        # Process files using FilePartitioner
        processed_files = partitioner.process_files(files_to_process)

        # Print statistics
        for file_path in processed_files:
            size = partitioner.get_file_size(file_path)
            print(f"{file_path.name}: {size} characters")

        # Generate chart for non-split files
        normal_files = [
            (f, partitioner.get_file_size(f))
            for f in processed_files
            if partitioner.get_file_size(f) <= threshold
        ]

        labels = [f.name for f, _ in normal_files]
        sizes = [s for _, s in normal_files]


    except ValueError as e:
        print(f"Error: Unable to satisfy constraints - {e}")
        return [], []

    plt.figure(figsize=(15, 10))
    plt.bar(range(len(sizes)), sizes)
    plt.xticks(range(len(labels)), labels, rotation=90)
    plt.title('File Sizes (in characters)')
    plt.xlabel('Files')
    plt.ylabel('Number of characters')
    plt.tight_layout()
    plt.savefig('file_sizes_chart.png')
