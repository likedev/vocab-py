from ass_parser import read_ass
from typing import List, Tuple
import json


def convert_milliseconds_to_time(milliseconds):
    hours = milliseconds // 3600000
    remaining_milliseconds = milliseconds % 3600000

    minutes = remaining_milliseconds // 60000
    remaining_milliseconds %= 60000

    seconds = remaining_milliseconds // 1000
    remaining_milliseconds %= 1000

    return f"{hours:02}:{minutes:02}:{seconds:02}.{remaining_milliseconds:03}"


def parse_caption(path: str):
    subtitles = []
    with open(path, 'r', encoding='utf-8') as file:
        ass_file = read_ass(file)

        for event in ass_file.events:
            start_time = event.start
            end_time = event.end
            text = event.text

            text = text.replace(r"\N{\fnCalibri Italic\fs14\1c&H3CF1F3&\blur2}", "____")
            ts = text.split("____")
            if len(ts) == 2:
                it = {
                    "start": int(start_time),
                    "end": int(end_time),
                    "start_s": convert_milliseconds_to_time(start_time),
                    "end_s": convert_milliseconds_to_time(end_time),
                    "zh": ts[0].strip(),
                    "en": ts[1].strip()
                }
                subtitles.append(it)
    return subtitles


if __name__ == '__main__':
    data = (parse_caption(
        r"E:\tmp\breakingbad\[zmk.pw][绝命毒师].S01-05+电影版.1080p.BluRay.x265-RARBG.YYeTS.Chs&Eng\Breaking.Bad.S01E01.2008.1080P.Blu-ray.x265.AC3￡cXcY@FRDS_track4_[chi].ass"))
