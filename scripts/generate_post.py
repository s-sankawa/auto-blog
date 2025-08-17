import os
import openai
import random
import time
from datetime import datetime
from zoneinfo import ZoneInfo

openai.api_key = os.getenv("OPENAI_API_KEY")

# --- 設定 ---
TOPIC_FILE = "topics.txt"
OUTPUT_DIR = "content"

# --- 関数定義 ---
def call_openai(prompt, retries=5, wait=30):
    for i in range(retries):
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role":"system","content":"あなたはポケモンニュースに詳しい日本語ライターです。"},
                          {"role":"user","content":prompt}],
                temperature=0.7,
                max_tokens=800,
            )
            return resp.choices[0].message.content.strip()
        except openai.error.RateLimitError:
            print(f"Rate limit hit. Waiting {wait} seconds before retry...")
            time.sleep(wait)
            wait *= 2
    raise Exception("Failed after multiple retries due to rate limiting.")

def pick_topic():
    with open(TOPIC_FILE, encoding="utf-8") as f:
        topics = [t.strip() for t in f if t.strip()]
    return random.choice(topics) if topics else "ポケモン"

def generate_post(topic: str):
    now = datetime.now(ZoneInfo("Asia/Tokyo"))
    print(f"Generating article for: {topic}")

    prompt = f"""
以下のテーマに関する「最新のニュースや動向」を整理して、日本語でブログ記事にまとめてください。

テーマ：{topic}

■ 記事の構成（Markdown形式）
- 冒頭：50～80字程度で概要を太字で
- 見出し（h2, h3）で構成する
- 最新ニュース（1～3件）＋それに対する解説や背景
- ファンに嬉しい豆知識や注目ポイントを追加
- 最後に「まとめ」として読者への呼びかけや展望を記載

上記のスタイルでお願いします。
"""

    content = call_openai(prompt)

    filename = f"{OUTPUT_DIR}/{now.strftime('%Y-%m-%d')}-{topic.replace('/', '-')}.md"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# {topic} の最新ニュースまとめ（{now.strftime('%Y-%m-%d')}）\n\n")
        f.write(content + "\n")

    print(f"Saved article: {filename}")

def main():
    topic = pick_topic()
    generate_post(topic)

if __name__ == "__main__":
    main()
