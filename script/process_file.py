import os
import re
import shutil
def rename_files_in_directory(directory):
    """
    遍历指定目录中的所有文件，并根据文件名中的季度和集数（如'S01E02'）重命名这些文件。

    :param directory: 要遍历的目录的路径。
    """
    for filename in os.listdir(directory):
        # 使用正则表达式匹配'S01E02'这样的模式
        match = re.search(r'S\d{2}E\d{2}', filename)
        if match:
            new_name = match.group() + os.path.splitext(filename)[1]
            old_file = os.path.join(directory, filename)
            new_file = os.path.join(directory, new_name)

            # 重命名文件
            os.rename(old_file, new_file)
            print(f"Renamed '{filename}' to '{new_name}'")

# 指定目录
def move_mp4_files(src_directory, dest_directory):
    """
    递归搜索源目录下的所有.mp4文件，并将它们移动到目标目录。

    :param src_directory: 要搜索的源目录。
    :param dest_directory: 目标目录，用于存放找到的.mp4文件。
    """
    for root, dirs, files in os.walk(src_directory):
        for file in files:
            if file.endswith('.mp4'):
                src_file = os.path.join(root, file)
                dest_file = os.path.join(dest_directory, file)

                # 移动文件
                shutil.move(src_file, dest_file)
                print(f"Moved '{src_file}' to '{dest_file}'")

if __name__ == '__main__':
    rename_files_in_directory(r'E:\迅雷下载\Breaking.Bad.S01.720p.BluRay.x264.DTS-WiKi')


