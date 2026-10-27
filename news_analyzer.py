from dotenv import load_dotenv
load_dotenv()

import os
import time
import feedparser
from google import genai
from google.genai import types, errors
from pydantic import BaseModel, Field

# ==========================================
# 1. データ構造の定義（定义AI返回的数据结构）
# ==========================================
class NewsEvaluation(BaseModel):
    importance_rank: str = Field(description="重要度ランク: 'S' (必読), 'A' (推奨), 'B' (流し読み) のいずれか")
    summary_3lines: list[str] = Field(description="ニュースの核心を突く3行の短い要約（各40文字以内）")
    reason: str = Field(description="なぜこの重要度なのか、ユーザーにどう関係するかの1行解説")
    category: str = Field(description="記事のカテゴリ（例：IT・テクノロジー、経済、社会、国際など）")

# ==========================================
# 2. データ収集：NHK RSSから最新ニュースを取得
# ==========================================
def fetch_nhk_news(limit: int = 3):
    rss_url = "https://www.nhk.or.jp/rss/news/cat0.xml"
    feed = feedparser.parse(rss_url)

    articles = []
    for entry in feed.entries[:limit]:
        articles.append({
            "title": entry.title,
            "summary": entry.summary,
            "link": entry.link,
            "published": entry.published
        })
    return articles

# ==========================================
# 3. AI処理：要約・重要度スコアリング（自動モデル検出＆フォールバック付き）
# ==========================================
def analyze_news_with_ai(client: genai.Client, article: dict, user_interests: str) -> NewsEvaluation:
    prompt = f"""
    あなたは優秀なニュースキュレーターAIです。
    以下のニュース記事を分析し、構造化データとして出力してください。

    【ユーザーの興味・属性】
    {user_interests}

    【評価基準（スコアリング基準）】
    - Sランク：社会全体・経済・日常生活に極めて大きな影響がある重大ニュース、またはユーザーのキャリアに直結する必読ニュース。
    - Aランク：業界のトレンドとして知っておくべきニュース、またはユーザーの興味に強く合致するニュース。
    - Bランク：緊急性が低い、またはゴシップ・局所的なニュース（タイトルだけで十分なもの）。

    【対象のニュース記事】
    タイトル: {article['title']}
    概要: {article['summary']}
    """

    # 1. アカウントで実際に利用可能なモデル一覧をGoogleから自動取得する（404エラーを根絶！）
    # try:
    #     available = [
    #         m.name for m in client.models.list()
    #         if "gemini" in m.name and "embedding" not in m.name and "vision" not in m.name and "2.5" not in m.name
    #     ]
    #     # flash系（高速モデル）を優先して先頭に並べる
    #     flash_models = [m for m in available if "flash" in m]
    #     other_models = [m for m in available if "flash" not in m]
    #     candidate_models = (flash_models + other_models)[:4]
    #     print(f"📋 検出された利用可能モデル候補: {candidate_models}")
    # except Exception:
    candidate_models = [
        "models/gemini-flash-lite-latest",
        "models/gemini-3.1-flash-lite-preview",
        "models/gemini-3-flash-preview",
        "models/gemini-flash-latest",
    ]

    # 2. 候補モデルを順番に試す
    for model_name in candidate_models:
        try:
            print(f"🤖 AI分析中... (使用モデル: {model_name})")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=NewsEvaluation,
                    temperature=0.2,
                    http_options=types.HttpOptions(timeout=20000),
                ),
            )
            print(f"✅ [{model_name}] でAI分析に成功しました！")
            return NewsEvaluation.model_validate_json(response.text)

        except errors.ServerError:
            print(f"⚠️ [{model_name}] が混雑しています (503)。次の候補モデルへ切り替えます...")
        except errors.ClientError as e:
            print(f"ℹ️ [{model_name}] はスキップ ({e.code})。次の候補モデルを試します...")
        except Exception as e:
            print(f"⚠️ [{model_name}] がタイムアウト ({type(e).__name__})。次を試します...")

    # 👇 注意ここのインデント（字下げ）！forループと同じ高さ（左端から半角スペース4つ）に揃える！
    # すべてのモデルが失敗した場合のみ、ここに到達してモックデータを返す
    print("💡 すべての外部APIが混雑しているため、開発用のモックデータ（Fallback）を使用します。")
    return NewsEvaluation(
        importance_rank="S",
        summary_3lines=[
            f"【AI要約】{article['title'][:20]}に関する重要ニュース",
            "セキュリティやIT業界の動向に直結する内容",
            "今後の企業の対応や続報に注視が必要"
        ],
        reason="IT業界への就職やセキュリティ動向の把握において重要度が高いため（モック出力）",
        category="IT・セキュリティ"
    )
# ==========================================
# 4. メイン実行処理（テスト実行）
# ==========================================
if __name__ == "__main__":
    client = genai.Client()

    user_profile = "日本のIT業界への就職を目指している学生。AI技術、Web開発、日本の経済動向やビザ・労働環境に関心がある。"

    print("📡 NHKから最新ニュースを取得中...\n" + "="*50)
    latest_news = fetch_nhk_news(limit=3)

    for i, article in enumerate(latest_news, 1):
        print(f"\n📰 元記事 {i}: {article['title']}")
        print(f"🔗 リンク: {article['link']}")

        result = analyze_news_with_ai(client, article, user_profile)

        print(f"🏆 【重要度: {result.importance_rank}ランク】 (カテゴリ: {result.category})")
        print(f"💡 理由: {result.reason}")
        print("📝 3行要約:")
        for line in result.summary_3lines:
            print(f"  ・{line}")
        print("-" * 50)

        # 連続リクエストによる制限（レートリミット）を防ぐため2秒待機
        time.sleep(2)
