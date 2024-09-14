def parse_txt(lines):
    book_content = []
    current_paragraph = []
    current_chapter_title = []

    for line in lines:
        line = line.strip()
        if line.startswith('<章节标题>'):
            if current_paragraph:
                book_content.append({'type': 'paragraph', 'content': ' '.join(current_paragraph)})
                current_paragraph = []
            current_chapter_title.append(line[6:])
        elif line == '<段落分隔符>':
            if current_paragraph:
                book_content.append({'type': 'paragraph', 'content': ' '.join(current_paragraph)})
                current_paragraph = []
            if current_chapter_title:
                book_content.append({'type': 'chapter_title', 'content': current_chapter_title})
                current_chapter_title = []
        else:
            if current_chapter_title:
                book_content.append({'type': 'chapter_title', 'content': current_chapter_title})
                current_chapter_title = []
            current_paragraph.append(line)

    # Add any remaining content
    if current_paragraph:
        book_content.append({'type': 'paragraph', 'content': ' '.join(current_paragraph)})
    if current_chapter_title:
        book_content.append({'type': 'chapter_title', 'content': current_chapter_title})

    # Import necessary modules
    from db import db
    import json
    import asyncio

    async def insert_book_content(book_content, book_id):
        for item in book_content:
            content_type = item['type']
            content = json.dumps(item['content'])

            sql = """
            INSERT INTO book_content (type, content, book_id)
            VALUES (%s, %s, %s)
            """
            params = (content_type, content, book_id)
            try:
                await db.execute(sql, params)
            except Exception as e:
                print(f"Error inserting content: {e}")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(insert_book_content(book_content, book_id=1))
    return book_content


def process_txt(path):
    with open(path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        parse_txt(lines)


if __name__ == '__main__':
    process_txt("output.txt")
