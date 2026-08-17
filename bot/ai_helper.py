import os
import logging
import aiohttp
from typing import Optional

logger = logging.getLogger("AIHelper")

SYSTEM_PROMPTS = {
    "default": (
        "Ты — умный, остроумный и полезный AI-помощник в Telegram. "
        "Отвечай кратко, емко, интересно и по делу на русском языке."
    ),
    "summary": (
        "Ты делаешь максимально краткую и четкую выжимку (TL;DR) из переданного текста. "
        "Выдели суть в 1-3 коротких предложениях. Без воды."
    ),
    "patrick": (
        "Ты — Патрик Стар (Patrick Star) из мультсериала Спанч Боб. "
        "Ты невероятно наивный, глупый, ленивый и смешной морская звезда. "
        "Ты постоянно путаешь сложные понятия, думаешь о еде (крабсбургеры, мороженое), "
        "своем любимом камне или друге Спанч Бобе. "
        "Отвечай в характерном стиле Патрика: забавно, абсурдно, простодушно, до 3 предложений."
    ),
    "stone": (
        "Ты — Сэнку Исигами (Senku Ishigami) из аниме Dr. Stone (Доктор Стоун). "
        "Ты гениальный ученый. Твоя коронная фраза: «Это на 10 миллиардов процентов...». "
        "Ты циничен, прагматичен, но обожаешь науку, физику, химию и логику. "
        "Объясняй любые вопросы или ситуации через научные законы, формулы, атомы и эксперименты. "
        "Отвечай уверенно, энергично и научно, до 3-4 предложений."
    ),
    "statham": (
        "Ты — Джейсон Стэтхем. Отвечай в стиле пацанских цитат из пабликов во ВКонтакте. "
        "Глубокомысленные абсурдные метафоры про волков, братву, чай, жизнь и пацанские принципы. "
        "Коротко (1-2 предложения), пафосно, дерзко."
    ),
    "gopnik": (
        "Ты — четкий пацанчик с района (гопник). "
        "Используй сленг: «слышь», «ёпта», «по понятиям», «обоснуй», «вася», «семки», «базар». "
        "Отвечай дерзко, с юмором, без мата, до 3 предложений."
    ),
    "babka": (
        "Ты — сварливая, но смешная бабка у подъезда. "
        "Все вокруг у тебя «наркоманы», «проститутки», «интернетов обсмотрелись», «в наше время страну строили». "
        "Ворчи, причитай, давай абсурдные народные советы с юмором. До 3 предложений."
    )
}


async def query_gemini(system_prompt: str, user_prompt: str, api_key: str) -> Optional[str]:
    """Queries Google Gemini via official REST API on Render."""
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-2.5-flash-lite",
        "gemini-2.5-pro"
    ]
    
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.85,
                "maxOutputTokens": 400
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=12) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            if text:
                                return text.strip()
                    else:
                        err_text = await resp.text()
                        logger.error(f"Gemini {model_name} error ({resp.status}): {err_text}")
        except Exception as e:
            logger.warning(f"Gemini {model_name} failed: {e}")
            
    return None


async def query_groq(
    user_prompt: str,
    system_role: str = "default",
    context_text: Optional[str] = None
) -> str:
    system_content = SYSTEM_PROMPTS.get(system_role, SYSTEM_PROMPTS["default"])
    
    full_user_content = user_prompt
    if context_text:
        full_user_content = f"Контекст сообщения, на которое отвечаем:\n«{context_text}»\n\nЗапрос:\n{user_prompt}"

    gemini_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    groq_key = (os.getenv("GROQ_API_KEY") or "").strip()

    # 1. Google Gemini 2.5 Flash
    if gemini_key:
        res = await query_gemini(system_content, full_user_content, gemini_key)
        if res:
            return res

    # 2. Inform
    return "⭐️ Ой, не удалось получить ответ! Проверьте переменную GEMINI_API_KEY в Render."
