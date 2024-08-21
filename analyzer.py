from pathlib import Path
import re
import matplotlib.pyplot as plt
import japanize_matplotlib


break_line_pattern = r"\n\n\n"

def clean_html_content(content):
    # HTMLタグを削除
    content = re.sub(r"<[^>]+>", "", content)

    # 各行の先頭の空白文字（\n以外）を削除
    content = re.sub(r"^[ \t]+", "", content, flags=re.MULTILINE)

    prev_content_len = len(content)

    # 4つ以上連続する空白行を3つの空白行に置換
    content = re.sub("\n{4,}", "\n\n\n", content)

    sub_content_len = len(content)
    print(f"Replaced {prev_content_len - sub_content_len} characters.")

    return content


def collect_and_process_html_files(folder_path, output_folder="./txt", pattern="*/*.html"):
    folder = Path(folder_path)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    
    processed_files = []
    
    for file_path in folder.rglob(pattern):
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

def analyze_consolidate_and_clean_files(output_folder, top_n=47):
    file_sizes = {}
    for file_path in Path(output_folder).glob('*.txt'):
        with file_path.open('r', encoding='utf-8') as f:
            content = f.read()
            file_sizes[file_path] = len(content)
    
    sorted_files = sorted(file_sizes.items(), key=lambda x: x[1], reverse=True)
    
    top_files = sorted_files[:top_n]
    other_files = sorted_files[top_n:]
    
    # 上位ファイルはそのままに
    for file_path, size in top_files:
        print(f"{file_path.name}: {size} characters")
    
    # 残りのファイルをothers.txtにまとめてから削除
    others_content = ""
    for file_path, _ in other_files:
        with file_path.open('r', encoding='utf-8') as f:
            others_content += f.read() + "\n\n"
        file_path.unlink()  # ファイルを削除
    
    others_path = Path(output_folder) / "others.txt"
    with others_path.open('w', encoding='utf-8') as f:
        f.write(others_content)
    
    # 棒グラフの生成
    labels = [f.name for f, _ in top_files] + ['others.txt']
    sizes = [s for _, s in top_files] + [len(others_content)]
    
    plt.figure(figsize=(15, 10))
    plt.bar(range(len(sizes)), sizes)
    plt.xticks(range(len(labels)), labels, rotation=90)
    plt.title('File Sizes (in characters)')
    plt.xlabel('Files')
    plt.ylabel('Number of characters')
    plt.tight_layout()
    plt.savefig('file_sizes_chart.png')
    
    return top_files, others_path, len(other_files)

# メイン処理
folder_path = "./html"
output_folder = "./txt"

processed_files = collect_and_process_html_files(folder_path, output_folder)
top_files, others_path, deleted_count = analyze_consolidate_and_clean_files(output_folder)

print(f"\nTop 47 files have been kept in their original state.")
print(f"{deleted_count} files have been consolidated into {others_path} and then deleted.")
print(f"A bar chart has been generated and saved as 'file_sizes_chart.png' in the output folder.")
