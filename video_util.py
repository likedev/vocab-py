 from moviepy.editor import VideoFileClip


def cut_video(source_path, start_time, end_time, output_path, resolution=(1280, 720)):
    """
    切割视频文件片段，并调整分辨率。

    :param source_path: 源视频文件路径。
    :param start_time: 切割开始时间，可以是以秒为单位的数字，也可以是格式化的字符串。
    :param end_time: 切割结束时间，可以是以秒为单位的数字，也可以是格式化的字符串。
    :param output_path: 输出视频文件路径。
    :param resolution: 输出视频的分辨率，格式为 (宽度, 高度)。
    """
    with VideoFileClip(source_path) as video:
        # 调整视频分辨率
        video = video.resize(resolution)

        # 切割视频
        new_video = video.subclip(start_time, end_time)

        # 写入视频文件
        # 可以调整比特率（bitrate）以进一步减小文件大小
        new_video.write_videofile(output_path, codec="libx264", audio_codec="aac", bitrate="400k")


if __name__ == '__main__':
    src = r"E:\迅雷下载\Breaking.Bad.S01.720p.BluRay.x264.DTS-WiKi\S01E01.mp4"
    dst = r"E:\迅雷下载\breakingbad-pieces\out1.mp4"
    cut_video(src, "00:22:37.500", "00:22:43.250", dst)
