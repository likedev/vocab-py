import re
import fitz  # PyMuPDF

"""
Check if the given text is likely a chapter title.

Args:
    text (str): The text to check.

Returns:
    bool: True if the text is likely a chapter title, False otherwise.
"""


def is_chapter(text):
    chapter_keywords = ['prologue', 'chapter', 'epilogue', 'part', 'section']
    words = text.split()
    return len(words) <= 5 and any(keyword in text.lower() for keyword in chapter_keywords)


def parse_pdf(pdf_path, txt_output):
    doc = fitz.open(pdf_path)
    result = []
    text_buffer = ""
    current_chapter = ""
    in_paragraph = False  # 指示当前是否在段落中

    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    spans = line["spans"]
                    line_text = ""
                    line_indent = None
                    for span in spans:
                        text = span["text"]
                        if not text.strip():
                            continue
                        text = text.replace("--", " ")

                        # 检查是否为章节标题
                        if span["size"] > 15 or is_chapter(text):  # 你可能需要调整这个阈值
                            # 处理缓冲区中的文本
                            if text_buffer:
                                sentences = re.split(r'(?<=[.!?;])\s+', text_buffer.strip())
                                result.extend(sentences)
                                text_buffer = ""
                            # 添加章节标题
                            chapter_title = f"<章节标题> {text.strip()}"
                            result.append(chapter_title)
                            in_paragraph = False
                            current_chapter = chapter_title
                        else:
                            # 获取行首缩进信息
                            if line_indent is None:
                                line_indent = span["origin"][0]
                            line_text += ' ' + text.strip()

                    if line_text:
                        # 根据缩进检测新段落
                        if line_indent is not None and line_indent >= 110:
                            print(f"Line indent: {line_indent}, Text: {line_text}")
                            # 行首有缩进，表示新段落
                            if text_buffer:
                                # 处理当前段落
                                sentences = re.split(r'(?<=[.!?])\s+', text_buffer.strip())
                                result.extend(sentences)
                                result.append('<段落分隔符>')  # 插入一个空行作为段落分隔符
                                text_buffer = line_text.strip()
                            else:
                                text_buffer = line_text.strip()
                            in_paragraph = True
                        else:
                            # 无缩进，继续累积文本
                            text_buffer += ' ' + line_text.strip()
                            in_paragraph = False

    # 处理最后的文本缓冲区
    if text_buffer:
        sentences = re.split(r'(?<=[.!?;])\s+', text_buffer.strip())
        result.extend(sentences)

    # 将结果写入txt文件
    with open(txt_output, 'w', encoding='utf-8') as f:
        for line in result:
            if line == '':
                f.write('\n')  # 段落分隔符
            else:
                line = line.strip()
                if line:
                    f.write(line + '\n')


if __name__ == "__main__":
    pdf_path = r"F:\books\英语\The_Big_Short__Inside_the_Doom.pdf"  # 替换为你的PDF文件路径
    txt_output = 'output.txt'  # 输出的txt文件名
    parse_pdf(pdf_path, txt_output)
