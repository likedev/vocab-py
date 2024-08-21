import os

if os.name == 'nt':
    UPLOAD_DIR_PATH = "C:/tmp/tmp"
    MYSQL_PASS = "root"
else:
    UPLOAD_DIR_PATH = "/opt/data/pic"
    MYSQL_PASS = "!kickyourASS899"
