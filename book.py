from db import db
import json
import asyncio
import openai
import config
import logging
from fastapi import APIRouter, HTTPException
from common import ok_data

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


async def translate_text(text):
    # Configure proxy
    print("chatgpt 输入:", text)
    openai.proxy = "http://127.0.0.1:9080"

    response = await openai.ChatCompletion.acreate(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system",
             "content": r'''Translate English to Chinese and format as JSON array. '''},
            {
                "role": "user",
                "content": "Hello world! How are you today?"
            },
            {
                "role": "assistant",
                "content": """
                { 
                    "text": [
                        {"en":"Hello world!","zh":"你好，世界！"},
                        {"en":"How are you today?","zh":"你今天好吗？"}
                    ]
                }
                """
            },
            {"role": "user", "content": text}
        ]
    )
    content = response.choices[0].message.content
    print(f"Raw GPT response:\n {content}")

    # Attempt to parse JSON
    translated_content = json.loads(content)

    # Validate JSON structure
    if not isinstance(translated_content, dict) or "text" not in translated_content:
        raise ValueError("Invalid JSON structure: missing 'text' key")

    translated_text = translated_content["text"]
    if not isinstance(translated_text, list):
        translated_text = [translated_text]

    if not all(isinstance(item, dict) and "en" in item and "zh" in item for item in translated_text):
        raise ValueError("Invalid JSON structure: 'text' should be a list of dictionaries with 'en' and 'zh' keys")
    return translated_text


async def translate_book_content(book_id, limit):
    """
    调用 chatgpt 3.5-turbo
    翻译 book_content 的 content 到  translated
    ,从 translated 为空的最小 id ，翻译 limit 个
    """

    # Get the book content items with empty translated field
    sql = """
    SELECT id, type, content
    FROM book_content
    WHERE book_id = %s AND translated IS NULL
    ORDER BY id
    LIMIT %s
    """
    params = (book_id, limit)
    items = await db.query(sql, params)

    translated_count = 0
    for item in items:
        content_type = item['type']
        content = json.loads(item['content'])
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if content_type == 'chapter_title':
                    translated_content = await translate_text(' '.join(content))
                elif content_type == 'paragraph':
                    translated_content = await translate_text(content)
                else:
                    logging.warning(f"Skipping unknown content type: {content_type}")
                    continue
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logging.warning(f"Attempt {attempt + 1} failed. Retrying... Error: {str(e)}")
                else:
                    logging.error(f"All {max_retries} attempts failed. Error: {str(e)}")
                    translated_content = None

        if translated_content:
            update_sql = """
            UPDATE book_content
            SET translated = %s
            WHERE id = %s
            """
            update_params = (json.dumps({"text": translated_content}), item['id'])
            await db.execute(update_sql, update_params)
            translated_count += 1
            logging.info(f"Successfully translated and updated item {item['id']}")
        else:
            logging.warning(f"Failed to translate item {item['id']}")

    return translated_count


async def main():
    # Assuming book_id 1 for demonstration purposes
    book_id = 1
    # Translate 10 items at a time
    limit = 100
    await translate_book_content(book_id, limit)


router = APIRouter()

import re
import vocab


def process_word(word):
    # Extract the word without punctuation
    clean_word = re.sub(r'[^\w\s]', '', word.lower())
    if clean_word:
        original_form = vocab.get_original_form(clean_word)
        word_data = vocab.vocab_data.get(original_form)
        if word_data:
            freq_rank = vocab.get_frequency_rank(original_form)
            if word_data['status'] != 'master' and freq_rank > 2000:
                # Preserve original punctuation
                return re.sub(clean_word, f"<keyword>{clean_word}</keyword>", word, flags=re.IGNORECASE)
    return word


def highlight_keywords(text):
    # Split text into words while preserving punctuation
    words = re.findall(r'\S+|\s+', text)
    highlighted_words = [process_word(word) for word in words]
    return ''.join(highlighted_words)


@router.get("/book-next-content")
async def book_next_batch_content(book_id: int, current_id: int, direction: str = "next"):
    if direction == "next":
        sql = """
        SELECT id, type, content, translated
        FROM book_content
        WHERE book_id = %s AND id > %s
        ORDER BY id
        LIMIT 1
        """
    elif direction == "prev":
        sql = """
        SELECT id, type, content, translated
        FROM book_content
        WHERE book_id = %s AND id < %s
        ORDER BY id DESC
        LIMIT 1
        """
    else:
        sql = """
        SELECT id, type, content, translated
        FROM book_content
        WHERE book_id = %s AND id = %s
        """
    params = (book_id, current_id)
    result = await db.query(sql, params)

    if not result:
        raise HTTPException(status_code=404, detail="No content available")

    item = result[0]

    translated = json.loads(item['translated']) if item['translated'] else None

    # Apply highlighting to translated text if available
    if translated and 'text' in translated:
        for it in translated['text']:
            if 'en' in it:
                it['en'] = highlight_keywords(it['en'])

    # Update the book's last_content_id
    update_sql = """
    UPDATE book
    SET last_content_id = %s
    WHERE id = %s
    """
    await db.execute(update_sql, (item['id'], book_id))

    return ok_data({
        "id": item['id'],
        "type": item['type'],
        "translated": translated
    })


@router.get("/books")
async def get_all_books():
    sql = """
    SELECT id, name, last_content_id
    FROM book
    ORDER BY id
    """
    result = await db.query(sql)
    return ok_data({"books": result})


@router.get("/book/{book_id}")
async def get_book_by_id(book_id: int):
    sql = """
    SELECT id, name, last_content_id
    FROM book
    WHERE id = %s
    """
    result = await db.query(sql, (book_id,))
    if not result:
        raise HTTPException(status_code=404, detail="Book not found")
    return ok_data(result[0])



