from deep_translator import GoogleTranslator

# Use any translator you like, in this example GoogleTranslator

eng_file = r"D:\code\py\video-eng-words\data\eng.txt"
translator = GoogleTranslator(source='en', target='zh-CN')

translated = translator.translate_file(eng_file)
print(translated)
