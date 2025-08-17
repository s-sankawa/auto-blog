import os, re, json, random, textwrap, time
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

# ==== 設定 ====
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY")  # 任意
TOPICS_FILE = "topics.txt"
NUM_POSTS_PER_DAY = 3         # 1日あたり生成記事数
WAIT_BETWEEN_POSTS = 300      # 秒単位（5分）

# ==== ユーティリティ ====
def today_jst():
    return datetime.now(ZoneInfo("Asia/Tokyo"))

def slugify(s: str) -> str:
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"[^\w\-ぁ-んァ-ヶ一-龥ー]", "", s)
    return s.lower()

def load_topics(filename):
    if not os.path.exists(filename):
        return ["AIトレンド"]
    with open(filename, encoding="utf-8") as f:
        topics = [t.strip() for t in f if t.strip()]
    return topics if topics else ["AIトレンド"]

def pick_topics(topics, k):
    return random.sample(topics, k=min(k, len(topics)))

def serper_search(q: str, num=5):
    if not SERPER_API_KEY:
        return []
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": q, "num": num}
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    out = []
    for it in data.get("organic", [])[:num]:
        out.append({"title": it.get("title", ""), "link": it.get("link", ""), "snippet": it.get("snippet", "")})
    return out

def call_openai(prompt, retries=5, backoff=30):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "system", "content": "あなたは日本語のSEOに詳しい編集者です。"},
                     {"role": "user", "content": prompt}],
        "temperature": 0.7,
    }

    for attempt in range(retries):
        r = requests.post(url, headers=headers, json=body)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        elif r.status_code == 429:
            wait = backoff * (attempt + 1)
            print(f"Rate limit hit. Waiting {wait} seconds before retry...")
            time.sleep(wait)
        else:
            r.raise_for_status()
    raise Exception("Failed after multiple retries due to rate limiting.")

def generate_post(topic):
    now = today_jst()
    sources = serper_search(topic, num=5)
    bullet_sources = "\n".join([f"- {s['title']}（{s['link']}）" for s in sources]) if sources else "（参考リンクなし / 生成ベース）"

    prompt = textwrap.dedent(f"""
    テーマ: 「{topic}」
    目的: GitHub Pages用ブログ記事。読者の検索意図を満たし、初学者にも分かりやすく。

    必須条件:
    - 日本語、Markdown形式（# 見出し、## 小見出し、箇条書き、表を適宜）
    - 冒頭に150字程度の要約（太字）
    - SEOを意識した構成（結論→根拠→具体例→FAQ→まとめ）
    - 具体例/手順/チェックリストを入れる
    - 可能なら内部で簡単な表（メリデメ等）を1つ
    - 最後に「参考リンク」節を設け、以下の候補を自然に要約しながら列挙（不要なら“参考リンク：なし”と記載）

    参考リンク候補:
    {bullet_sources}
    """)

    content_md = call_openai(prompt)

    title = f"{topic}の最新ガイド（{now.strftime('%Y-%m-%d')}）"
    slug = slugify(topic)
    filename = f"_posts/{now.strftime('%Y-%m-%d')}-{slug}.md"
    os.makedirs("_posts", exist_ok=True)
    front = textwrap.dedent(f"""\
    ---
    layout: post
    title: "{title}"
    date: {now.strftime('%Y-%m-%d %H:%M:%S %z')}
    tags: [{topic}]
    ---
    """)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front + "\n" + content_md + "\n")
    print(f"Generated: {filename}")

# ==== メイン処理 ====
def main():
    assert OPENAI_API_KEY, "OPENAI_API_KEY が未設定です（GitHub Secretsで設定）"
    topics = load_topics(TOPICS_FILE)
    selected_topics = pick_topics(topics, NUM_POSTS_PER_DAY)

    for idx, topic in enumerate(selected_topics):
        print(f"Generating post {idx+1}/{len(selected_topics)}: {topic}")
        generate_post(topic)
        if idx < len(selected_topics) - 1:
            print(f"Waiting {WAIT_BETWEEN_POSTS} seconds before next post...")
            time.sleep(WAIT_BETWEEN_POSTS)

if __name__ == "__main__":
    main()
