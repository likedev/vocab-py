import json
from collections import defaultdict
from db import db

# Global variables to store the vocabulary data
vocab_data = {}
word_to_original = {}
frequency_rank = {}


async def load_vocab_data():
    global vocab_data, word_to_original, frequency_rank
    # Fetch all vocabulary data from the database
    sql = "SELECT word, tier, related, freq, status, ext FROM vocab"
    result = await db.query(sql)
    # Process the data
    for row in result:
        word = row['word']
        vocab_data[word] = {
            'tier': row['tier'],
            'related': json.loads(row['related']) if row['related'] else [],
            'freq': row['freq'],
            'status': row['status'],
            'ext': json.loads(row['ext']) if row['ext'] else {}
        }
        # Calculate original form
        rel_arr = vocab_data[word]['related']
        if rel_arr:
            for rel in rel_arr:
                word_to_original[rel[0]] = word
        else:
            word_to_original[word] = word

    # Calculate frequency rank
    sorted_words = sorted(vocab_data.items(), key=lambda x: x[1]['freq'], reverse=True)
    for rank, (word, _) in enumerate(sorted_words, 1):
        frequency_rank[word] = rank


async def initialize_vocab():
    await load_vocab_data()
    print(f"Loaded {len(vocab_data)} words into memory")
    print(f"Calculated {len(word_to_original)} word-to-original mappings")
    print(f"Ranked {len(frequency_rank)} words by frequency")


# Function to get the original form of a word
def get_original_form(word):
    return word_to_original.get(word, word)


# Function to get the frequency rank of a word
def get_frequency_rank(word):
    return frequency_rank.get(word, -1)
