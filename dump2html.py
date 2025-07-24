import argparse
import glob
import json
import os
import datetime


"""
Slack からエクスポートした JSON データを HTML 形式に変換します。
以下のように実行してください。

python slack_json_to_html.py \
  -i "~/Downloads/StatML-Reading Slack export Jul 29 2022 - Jul 14 2024" \
  -o "~/20240714" \
  -c "random,book-vaart-2000"

-i はエクスポートデータを解凍したフォルダを、
-o にはダンプ先フォルダを指定してください。
-c にはダンプ対象チャンネルをカンマ区切りで指定してください
(エクスポートデータのサブフォルダ名と一致させてください)。

上のように実行した場合、以下のファイルが生成されます。
- ~/20240714/random.html
- ~/20240714/book-vaart-2000.html
"""


class HtmlWriter:
    """ HTML ファイルを一つ書き出す便利クラスです。
    """
    def write(self, s):
        self.obh.write(s + '\n')
    def _write_styles(self):
        self.write('<style>')
        for k, v in self.styles.items():
            self.write(k + ' {')
            for kk, vv in v.items():
                self.write('  ' + kk + ': ' + vv + ';')
            self.write('}') 
        self.write('</style>')
    def __init__(self, title, out_html):
        self.styles = {
            'body': {'width': '690px', 'font-family': '"Trebuchet MS", sans-serif', 'margin': '15px'},
            'table': {'border-collapse': 'collapse', 'margin': '10px 0'},
            'th, td': {'border': '1px solid black', 'font-size': '13px', 'padding': '3px'},
            'tr td:nth-of-type(1)': {'width': '100px', 'background': '#f0f0f0'},
            'tr td:nth-of-type(2)': {'width': '500px', 'word-break': 'break-all'}}
        self.obh = open(out_html, mode='w', encoding='utf-8', newline='\n')
        self.write('<html>')
        self.write('<head>')
        self.write('<meta charset="UTF-8"/>')
        self.write('<meta name="viewport" content="width=device-width, initial-scale=1.0"/>')
        self.write(f'<title>{title}</title>')
        self._write_styles()
        self.write('</head>')
        self.write('<body>')
    def close(self):
        self.write('</body>')
        self.write('</html>')
        self.obh.close()


class TableWriter:
    """ テーブルを一つ書き出す便利クラスです。
    """
    def __init__(self, html_writer):
        self.hw = html_writer
        self.hw.write('<table>\n')
    def write(self, *args):
        self.hw.write('<tr>\n')
        for v in args:
            self.hw.write(f'<td>{v}</td>\n')
        self.hw.write('</tr>\n')
    def close(self):
        self.hw.write('</table>\n')


class SlackJsonToHtml:
    """ Slack からエクスポートした JSON データを HTML 形式に変換します。
    """
    def __init__(self, in_dir, out_dir, channel_names):
        self.in_dir = in_dir
        self.out_dir = out_dir

        # ユーザIDと名前の対応辞書をつくります。
        with open(os.path.join(self.in_dir, 'users.json'), mode='r', encoding='utf-8') as ojf:
            data_users = json.load(ojf)
        self.users = {user['id']: user['real_name'] for user in data_users}

        # 対象チャンネルをダンプします。
        for channel_name in channel_names:
            self.dump_channel(channel_name)

    def to_str(self, *args):
        # args に渡された要素を文字列化し、ユーザ ID と HTML 特殊文字を解決します。
        s = '\n'.join([str(v) for v in args])
        for k, v in self.users.items():
            s = s.replace(k, v)
        s = s.replace('<', '&lt;')
        s = s.replace('>', '&gt;')
        s = s.replace('\n', '<br/>')
        return s

    def dump_channel(self, channel_name):
        # そのチャンネルのフォルダから全ての投稿を収集します。
        json_files = glob.glob(os.path.join(self.in_dir, channel_name, '*.json'))
        posts = []
        for json_file in json_files:
            with open(json_file, mode='r', encoding='utf-8') as ojf:
                posts += json.load(ojf)

        # 投稿をスレッドごとに束ねます。
        threads = []
        threads_ts = {}  # スレッド先頭時刻からそのスレッドを格納したインデクスへの辞書です。
        for post in posts:
            if 'user' not in post:
                post['user'] = 'BOT'  # user フィールドがないとき便宜的に BOT とします。
            ts = int(float(post['ts']))
            post['ts'] = datetime.datetime.fromtimestamp(ts)
            if 'thread_ts' in post:  # thread_ts フィールドがあるときスレッドができています。
                ts = int(float(post['thread_ts']))
                post['thread_ts'] = datetime.datetime.fromtimestamp(ts)
                if post['thread_ts'] in threads_ts:
                    threads[threads_ts[post['thread_ts']]].append(post)
                else:
                    threads.append([post])
                    threads_ts[post['thread_ts']] = len(threads) - 1
            else:  # thread_ts フィールドがない投稿はスレッドになっておらず単独で格納します。
                threads.append([post])

        # スレッド先頭日時降順に HTML に書き出します。
        out_html = os.path.join(self.out_dir, channel_name + '.html')
        hw = HtmlWriter(channel_name, out_html)
        for thread in reversed(threads):  # 昇順がよいときは reversed() を除去してください。
            tw = TableWriter(hw)
            for post in thread:
                tw.write(self.to_str(post['user'], post['ts']), self.to_str(get_text(post)))
            tw.close()
        hw.close()


def get_text(item) -> str:
    try:
        if item['type'] == 'message':
            files = ""
            if 'files' in item:
                files = ", ".join([f"({b['name']})" for b in (item['files'] or [])])
            if 'text' in item:
                return f"{item['text']} {files}"
            return "\n".join([get_text(b) for b in (item['blocks'] or [])]) + files
        elif item['type'] == 'rich_text':
            return "\n".join([get_text(b) for b in item['elements']])
        elif item['type'] == 'rich_text_section':
            return "\n".join([get_text(b) for b in item['elements']])
        elif item['type'] == 'text':
            return item['text']
        elif item['type'] == 'canvas':
            return ""
        elif item['type'] == 'emoji':
            return ''
        elif item['type'] == 'link':
            return item['text']
        elif item['type'] == 'user':
            return ""
        else:
            raise ValueError(f"Unknown type: {item['type']}, {item}")
    except Exception as e:
        print(item)
        raise e

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--in_dir', required=True)
    parser.add_argument('-o', '--out_dir', required=True)
    parser.add_argument('-c', '--channel_names', required=True)
    args = parser.parse_args()

    in_dir = os.path.expanduser(args.in_dir)
    out_dir = os.path.expanduser(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    SlackJsonToHtml(in_dir, out_dir, args.channel_names.split(','))