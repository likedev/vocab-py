import os
import pprint

from script.caption_parser import parse_caption
from spider.crawlEapfoundation import get_eap_word_map, get_alias_map
from video_util import cut_video


def find_all_video_sub_path():
    videos = r"E:\迅雷下载\Breaking.Bad.S01.720p.BluRay.x264.DTS-WiKi"
    subtitle_dir_path = r"E:\tmp\breakingbad\[zmk.pw][绝命毒师].S01-05+电影版.1080p.BluRay.x265-RARBG.YYeTS.Chs&Eng"
    ll = []
    for root, dirs, files in os.walk(videos):
        for f in files:
            pp = os.path.join(root, f)
            subtitle_path = os.path.join(subtitle_dir_path, f.replace('.mp4', '.ass'))
            ll.append((pp, subtitle_path, f))
    return ll


EAP_ALIAS_MAP = None
EAP_WORD_MAP = None


def find_word_by_en(en):
    en = en.replace('...', " ")
    en = en.replace('.', " ")
    en = en.replace('?', " ")
    en = en.replace('!', " ")
    en = en.replace(',', " ")
    ll = en.split(" ")
    ll = [i.lower() for i in ll if len(i) > 0]
    res = []
    for w in ll:
        if w not in EAP_ALIAS_MAP:
            continue
        actual_word = EAP_ALIAS_MAP[w]
        if actual_word not in res:
            res.append(actual_word)
    return res


DEBUG = True


def debug(msg):
    global DEBUG
    if DEBUG:
        print(msg)


def cal_sub_context(subtitle_data_list, idx):
    def is_half_sentence(_i):
        if _i > len(subtitle_data_list) - 1 or _i < 0:
            return False
        en_txt = subtitle_data_list[_i]["en"]
        if not en_txt:
            return False
        en_txt = en_txt.strip()
        return "?" in en_txt or "?" in en_txt or not (en_txt.endswith(".") or en_txt.endswith("。"))

    this_sub = subtitle_data_list[idx]
    res = {}

    sub_list = [this_sub]
    # 向前遍历
    i = idx - 1
    # 如果是半句
    while i >= 0:
        if (is_half_sentence(i)) and idx - i <= 3:
            sub_list.insert(0, subtitle_data_list[i])
            debug("往前，是半句" + subtitle_data_list[i]["en"])
            i -= 1
            break
        if idx - i >= 6:
            break
        if abs(subtitle_data_list[i]["end"] - subtitle_data_list[i + 1]["start"]) >= 1500:
            debug("往前，中间间隔超过时间")
            break
        if abs(subtitle_data_list[i]["start"] - subtitle_data_list[idx]["start"]) >= 5000:
            debug("往前，距离目标太远")
            break
        sub_list.insert(0, subtitle_data_list[i])
        debug("往前，加入" + subtitle_data_list[i]["en"])
        i -= 1
    # 向后遍历
    i = idx + 1
    while i < len(subtitle_data_list):
        if (is_half_sentence(i - 1)) and i - idx <= 3:
            sub_list.append(subtitle_data_list[i])
            debug("往后，是半句" + subtitle_data_list[i]["en"])
            i += 1
            continue
        if i - idx >= 4:
            debug("下标超过" + subtitle_data_list[i]["en"])
            break
        if abs(subtitle_data_list[i]["start"] - subtitle_data_list[idx]["end"]) >= 3000:
            debug("往后，距离目标太远")
            break
        if abs(subtitle_data_list[i]["start"] - subtitle_data_list[i - 1]["end"]) >= 1500:
            debug("往后，中间间隔超过时间")
            break
        sub_list.append(subtitle_data_list[i])
        debug("往后，加入" + subtitle_data_list[i]["en"])
        i += 1
    for sub in sub_list:
        debug("[ %s , %s ] %s" % (sub["start"], sub["end"], sub["en"]))
    res["list"] = sub_list
    res["all_start"] = sub_list[0]["start"]
    res["all_start_s"] = sub_list[0]["start_s"]
    res["all_end"] = sub_list[-1]["end"]
    res["all_end_s"] = sub_list[-1]["end_s"]
    debug("总时长: %d " % ((int(res["all_end"]) - int(res["all_start"])) / 1000.0))
    return res


def all_contains(all_words, keywords):
    for word in keywords:
        if word not in all_words:
            return False
    return True


import re


def parse_series_episode(file):
    match = re.search(r'S(\d+)E(\d+)', file)
    if match:
        season, episode = match.groups()
        return int(season), int(episode)
    else:
        return 0, 0


import dao

if __name__ == '__main__':

    min_freq = 3000

    EAP_ALIAS_MAP = get_alias_map(min_freq=min_freq)
    EAP_WORD_MAP = get_eap_word_map(min_freq=min_freq)

    ll_list = find_all_video_sub_path()
    print("字幕和视频路径")
    pprint.pprint(ll_list)
    all_keywords = []

    for ll in ll_list:

        file_name = ll[2]
        series, episode = parse_series_episode(file_name)
        # 一个字幕
        sub_fpath = ll[1]
        video_fpath = ll[0]
        subtitle_data_list = parse_caption(sub_fpath)
        for i in range(len(subtitle_data_list)):
            sub_info = subtitle_data_list[i]
            en_text = sub_info["en"]
            keywords = find_word_by_en(en_text)
            if len(keywords) == 0 or all_contains(all_keywords, keywords):
                continue
            # 增加上下文
            print("keywords", keywords)
            ctx = cal_sub_context(subtitle_data_list, i)
            # print(ctx)
            ass_f_name = ll[2]
            out_f_name = ass_f_name.replace(".mp4", "") + f"_{ctx['all_start']}_{ctx['all_end']}.mp4"
            out_f_path = os.path.join(r"E:\迅雷下载\breakingbad-pieces", out_f_name)

            cut_video(video_fpath, ctx["all_start_s"], ctx["all_end_s"], out_f_path)
            all_keywords.extend(keywords)
            for w in keywords:
                new_record = {
                    'word': w,
                    'video_local': out_f_path,
                    'video_url': '',
                    's': series,
                    'p': episode,
                    'start': int(ctx['all_start']),
                    'end': int(ctx['all_end']),
                    'title': '绝命毒师'
                }
                dao.insert_record(new_record)

    all_keywords = list(set(all_keywords))

    print("Total keywords: ", len(all_keywords))
    pprint.pprint(all_keywords)
