import os
import openai

if os.name == 'nt':
    UPLOAD_DIR_PATH = "C:/tmp/tmp"
    MYSQL_PASS = "root"
else:
    UPLOAD_DIR_PATH = "/opt/data/pic"
    MYSQL_PASS = "!kickyourASS899"

OPENAI_KEY = "sk-proj-vFDOugMVNlu9CJ0ZhiqqT3BlbkFJLXns0NeBLnKfIYP2a26O"

openai.api_key = OPENAI_KEY
os.environ['OPENAI_API_KEY'] = OPENAI_KEY