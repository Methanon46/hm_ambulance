import datetime

# 和暦情報
ERA_DICT = {
    '令和': datetime.datetime(2019, 5, 1),
    '平成': datetime.datetime(1989, 1, 8),
    '昭和': datetime.datetime(1926, 12, 25),
    '大正': datetime.datetime(1912, 7, 30),
    '明治': datetime.datetime(1868, 1, 25),
}

# 和暦文字列出力関数
def format_date(date_obj, format_string):
    eras_filter = filter(lambda x: ERA_DICT[x] <= date_obj, ERA_DICT)
    era = max(eras_filter, key=lambda x: ERA_DICT[x])
    jp_year = str(date_obj.year - ERA_DICT[era].year + 1)
    jp_format = format_string.replace('%g', era).replace('%e', jp_year)
    return date_obj.strftime(jp_format)

# 和暦文字列解析関数
def parse_date(date_string, format_string):
    # 候補リスト作成
    eras = [e for e in ERA_DICT.keys() if e in date_string]
    jp_years = [str(n) for n in range(1, 10) if str(n) in date_string]

    # 元号に対して解析処理を繰り返す
    for era in eras:
        try:
            temp_format = format_string.replace('%g', era).replace('%e', '%y')
            date_obj = datetime.datetime.strptime(date_string, temp_format)
            jp_year = ERA_DICT[era].year + int(date_obj.strftime('%y')) - 1
            date_obj = date_obj.replace(year=jp_year)
            return date_obj
        except ValueError:
            pass

    # 1桁の年度と元号に対して解析処理を繰り返す
    for y in jp_years:
        for era in eras:
            try:
                temp_format = format_string.replace('%g', era).replace('%e', y)
                date_obj = datetime.datetime.strptime(date_string, temp_format)
                jp_year = ERA_DICT[era].year + int(y) - 1
                date_obj = date_obj.replace(year=jp_year)
                return date_obj
            except ValueError:
                pass
                
    # うるう年対応
    if '29' in date_string and '%d' in format_string:
         new_format_string = format_string.replace('%d', '29')
         date_obj = parse_date(date_string, new_format_string)
         date_obj = date_obj.replace(day=29)
         return date_obj

# テスト実行
if __name__ == '__main__':
    # 和暦から西暦への変換 (1)
    date_obj = parse_date('平成31年4月30日', '%g%e年%m月%d日')
    print(date_obj.strftime('%Y年%m月%d日')) # -> 2019年04月30日

    # 和暦から西暦への変換 (2)
    date_obj = parse_date('令和1年5月1日', '%g%e年%m月%d日')
    print(date_obj.strftime('%Y年%m月%d日')) # -> 2019年05月01日

    # 西暦から和暦への変換 (1)
    date_obj = datetime.datetime.strptime('2019年4月30日', '%Y年%m月%d日')
    print(format_date(date_obj, '%g%e年%m月%d日')) # -> 平成31年04月30日

    # 西暦から和暦への変換 (2)
    date_obj = datetime.datetime.strptime('2019年5月1日', '%Y年%m月%d日')
    print(format_date(date_obj, '%g%e年%m月%d日')) # -> 令和1年05月01日
    
    # うるう年のテスト(和暦から西暦)
    date_obj = parse_date('令和2年2月29日', '%g%e年%m月%d日')
    print(date_obj.strftime('%Y年%m月%d日')) # -> 2020年02月29日

    # うるう年のテスト(西暦から和暦)
    date_obj = datetime.datetime.strptime('2020年02月29日', '%Y年%m月%d日')
    print(format_date(date_obj, '%g%e年%m月%d日')) # -> 令和2年02月29日

