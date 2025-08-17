# scripts/generate_post.py
import os, re, json, random, textwrap
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

# ==== 設定 ====
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY")  # 任意
TOPICS_FILE = "topics.txt"

# ==== ユーティリティ ====
def today_jst():
    return datetime.now(ZoneInfo("Asia/Tokyo"))

def slugify(s: str) -> str:
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"[^\w\-ぁ-んァ-ヶ一-龥ー]", "", s)
    return s.lower()

def pick_topic():
    if not os.path.exists(TOPICS_FILE):
        return "AIトレンド"
    with open(TOPICS_FILE, encoding="utf-8") as f:
        topics = [t.strip() for t in f if t.strip()]
    return random.choice(topics) if topics else "AIトレンド"

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

def call_openai(prompt: str) -> str:
    # OpenAIの新SDKに合わせたHTTP呼び出し（依存軽量化のためrequestsを使用）
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "system", "content": "あなたは日本語のSEOに詳しい編集者です。"},
                     {"role": "user", "content": prompt}],
        "temperature": 0.7,
    }
    r = requests.post(url, headers=headers, data=json.dumps(body), timeout=90)
    r.raise_for_status()
    j = r.json()
    return j["choices"][0]["message"]["content"].strip()

# ==== メイン処理 ====
def main():
    assert OPENAI_API_KEY, "OPENAI_API_KEY が未設定です（GitHub Secretsで設定してください）"
    now = today_jst()
    topic = os.environ.get("TOPIC") or pick_topic()

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

    # Jekyll用フロントマター
    title = f"{topic}の最新ガイド（{now.strftime('%Y-%m-%d')}）"
    slug = slugify(topic) or "post"
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

if __name__ == "__main__":
    main()
