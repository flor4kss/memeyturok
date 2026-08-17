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


async def query_groq(
    user_prompt: str,
    system_role: str = "default",
    context_text: Optional[str] = None
) -> str:
    system_content = SYSTEM_PROMPTS.get(system_role, SYSTEM_PROMPTS["default"])
    
    full_user_content = user_prompt
    if context_text:
        full_user_content = f"Контекст сообщения, на которое отвечаем:\n«{context_text}»\n\nЗапрос/комментарий:\n{user_prompt}"

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": full_user_content}
    ]

    api_key = (os.getenv("GROQ_API_KEY") or "").strip()

    # 1. Try Groq API
    if api_key:
        models_to_try = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "gemma2-9b-it"
        ]
        
        for model_name in models_to_try:
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "model": model_name,
                        "messages": messages,
                        "temperature": 0.85,
                        "max_tokens": 400
                    }
                    async with session.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=12
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            content = data["choices"][0]["message"]["content"].strip()
                            if content:
                                return content
                        else:
                            err = await resp.text()
                            logger.error(f"Groq {model_name} error ({resp.status}): {err}")
            except Exception as e:
                logger.warning(f"Failed Groq model {model_name}: {e}")

    # 2. Fallback free gateway (Pollinations text)
    try:
        async with aiohttp.ClientSession() as session:
            combined = f"{system_content}\n\nЗапрос: {full_user_content}"
            async with session.post(
                "https://text.pollinations.ai/",
                json={"messages": [{"role": "user", "content": combined}], "model": "openai"},
                timeout=12
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if text and not text.startswith("<!DOCTYPE") and len(text) > 2:
                        return text.strip()
    except Exception as e:
        logger.warning(f"Fallback AI failed: {e}")

    return "⭐️ Ой, я кажется забыл, о чем думал... (Проверьте, сделан ли Deploy на Render после добавления GROQ_API_KEY)"
