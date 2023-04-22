import re
import os
from langchain.text_splitter import CharacterTextSplitter

def langchain_splitter(text, max_tokens=1000):
    text_splitter = CharacterTextSplitter(chunk_size=max_tokens, chunk_overlap=0)
    articles = {f"Chunk {i + 1}": {"text": chunk} for i, chunk in enumerate(text_splitter.split_text(text))}
    return articles


def txt_to_text(file_name):
    with open(file_name, 'r') as f:
        text = f.read()
    return text


def split_law_document(file_name, use_langchain_splitter=False):
    if use_langchain_splitter:
        return langchain_splitter(text)

    def process_article(prev_article_start, end_position, current_part):
        text_part = text[prev_article_start:end_position]
        text_part = text_part.split("___________")[0]

        article_dicts = []

        if len(text_part.split()) > 1000:
            half_length = len(text_part) // 2
            split_index = text_part[:half_length].rfind("\n")

            text_part_1 = text_part[:split_index]
            text_part_2 = text_part[split_index:]

            article_dicts.extend([
                {"text": text_part_1, "part_number": current_part["number"], "part_title": current_part["title"]},
                {"text": text_part_2, "part_number": current_part["number"], "part_title": current_part["title"]}
            ])
        else:
            article_dicts.append({"text": text_part, "part_number": current_part["number"], "part_title": current_part["title"]})

        return article_dicts

    articles = {}
    text = txt_to_text(file_name)

    part_matches = re.finditer(r'^_{11}\n(.+?)\n(.+?)\n', text, re.MULTILINE)
    article_matches = re.finditer(r'\n\s*((\d+[A-Z]?)[.]\s*(?:\t)?\s*.+?)\n', text)

    current_part = {"number": "Part I", "title": "Preliminary"}

    prev_article_key = prev_article_start = part_match = None

    part_match = next(part_matches, None)

    for match in article_matches:
        article_key = match.group(1)
        article_start = match.start()

        if prev_article_start is not None:
            end_position = article_start
            article_dicts = process_article(prev_article_start, end_position, current_part)
            for a in article_dicts:
                articles[prev_article_key] = a

        while part_match and part_match.start() < article_start:
            current_part["number"] = part_match.group(1)
            current_part["title"] = part_match.group(2)
            part_match = next(part_matches, None)

        prev_article_key = article_key
        prev_article_start = article_start

    if prev_article_start is not None:
        end_position = part_match.start() if part_match else len(text)
        article_dicts = process_article(prev_article_start, end_position, current_part)
        for a in article_dicts:
            articles[prev_article_key] = a

    return articles

def loadOrdinance(use_langchain_splitter=False):
    ordinances_path = "Ordinances"
    processed, meta = [], []

    for file in os.listdir(ordinances_path):
        if file.endswith(".txt"):
            file_path = os.path.join(ordinances_path, file)
            articles = split_law_document(file_path, use_langchain_splitter)

            for key, value in articles.items():
                processed.append(value["text"])
                if use_langchain_splitter:
                    meta.append({"Ordinance": file[:-4]})
                else:
                    meta.append({"Article": key, "Part": value["part_number"], "Part_title": value["part_title"], "Ordinance": file[:-4]})

    return processed, meta