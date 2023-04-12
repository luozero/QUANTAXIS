# coding: utf-8
#
# The MIT License (MIT)
#
# Copyright (c) 2016-2021 yutiansut/QUANTAXIS
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import json
import re
import pandas as pd
import time
from functools import partial
import akshare as ak
import efinance as ef
# import tushare as ts
from QUANTAXIS.QAUtil.QASql import ASCENDING, DESCENDING
from typing import List, Tuple, Union
from QUANTAXIS.QAUtil import (
    DATABASE, 
    QA_util_date_int2str,
    QA_util_date_stamp,
    QASETTING,
    QA_util_log_info,
    QA_util_to_json_from_pandas
)

def QA_fmt_code(code: str, style: str = None):
    """
    对股票代码格式化处理

    ---
    :param code: 股票代码
    :param style: 代码风格
    """
    pattern = re.compile(r"\d+")
    code = pattern.findall(code)[0]
    if style in ["jq", "joinquant", "聚宽"]:
        return code + ".XSHG" if code[0] == "6" else code + ".XSHE"
    if style in ["wd", "windcode", "万得"]:
        return code + ".SH" if code[0] == "6" else code + ".SZ"
    if style in ["gm", "goldminer", "掘金"]:
        return "SHSE." + code if code[0] == "6" else "SZSE." + code
    if style in ["ss", "skysoft", "天软"]:
        return "SH" + code if code[0] == "6" else "SZ" + code
    if style in ["ts", "tushare", "挖地兔"]:
        return code + ".SH" if code[0] == "6" else code + ".SZ"
    else:
        return code


def QA_fmt_code_list(code_list: Union[str, Tuple[str], List[str]], style: str = None):
    """
    为了适应不同行情源股票代码，加入对股票代码格式化的操作, 目前支持 “聚宽” “掘金” “万得” “天软”
    股票代码格式格式化

    参数
    ---
    :param code_list: 股票代码或列表
    :param style: 行情源
    """

    if isinstance(code_list, str):
        return [QA_fmt_code(code_list, style)]
    else:
        fmt_code = partial(QA_fmt_code, style=style)
        return list(map(fmt_code, code_list))

def QA_fetch_get_stock_adj(code, end=''):
    """获取股票的复权因子

    Arguments:
        code {[type]} -- [description]

    Keyword Arguments:
        end {str} -- [description] (default: {''})

    Returns:
        [type] -- [description]
    """

    # pro = get_pro()
    # adj = pro.adj_factor(ts_code=code, trade_date=end)
    # return adj


def QA_get_stock_basic():
    """
    沪深京 A 股列表
    :return: 沪深京 A 股数据
    :rtype: pandas.DataFrame
    """
    big_df = pd.DataFrame()
    stock_sh = ak.stock_info_sh_name_code(symbol="主板A股")
    stock_sh = stock_sh[["证券代码", "证券简称", "上市日期"]]

    stock_sz = ak.stock_info_sz_name_code(indicator="A股列表")
    stock_sz["A股代码"] = stock_sz["A股代码"].astype(str).str.zfill(6)
    big_df = pd.concat([big_df, stock_sz[["A股代码", "A股简称", "A股上市日期"]]], ignore_index=True)
    big_df.columns = ["证券代码", "证券简称", "上市日期"]

    stock_kcb = ak.stock_info_sh_name_code(symbol="科创板")
    stock_kcb = stock_kcb[["证券代码", "证券简称", "上市日期"]]

    stock_bse = ak.stock_info_bj_name_code()
    stock_bse = stock_bse[["证券代码", "证券简称", "上市日期"]]
    stock_bse.columns = ["证券代码", "证券简称", "上市日期"]

    big_df = pd.concat([big_df, stock_sh], ignore_index=True)
    big_df = pd.concat([big_df, stock_kcb], ignore_index=True)
    big_df = pd.concat([big_df, stock_bse], ignore_index=True)
    big_df.columns = ["code", "name", "list_date"]

    stock_base = big_df
    ef_stock_info = ef.stock.get_base_info(stock_base['code'])

    if len(ef_stock_info) > 0 :
      ef_stock_base_info = ef_stock_info[['净利润', '总市值', '流通市值', '所处行业', '市盈率(动)', '市净率', 'ROE', '毛利率', '净利率', '板块编号']]
      ef_stock_base_info.columns = ['profit', 'total_market_value', 'flow_market_value', 'indurstry', 'PE', 'RIC', 'ROE', 'gross_profit_ratio', 'net_profit_ratio', 'eastmoney_block']
      stock_base = pd.concat([stock_base, ef_stock_base_info], axis=1)


    return stock_base


def cover_time(date):
    """
    字符串 '20180101'  转变成 float 类型时间 类似 time.time() 返回的类型
    :param date: 字符串str -- 格式必须是 20180101 ，长度8
    :return: 类型float
    """
    datestr = str(date)[0:8]
    date = time.mktime(time.strptime(datestr, '%Y%m%d'))
    return date


def _get_subscription_type(if_fq):
    if str(if_fq) in ['qfq', '01']:
        if_fq = 'qfq'
    elif str(if_fq) in ['hfq', '02']:
        if_fq = 'hfq'
    elif str(if_fq) in ['bfq', '00']:
        if_fq = None
    else:
        QA_util_log_info('wrong with fq_factor! using qfq')
        if_fq = 'qfq'
    return if_fq


def QA_fetch_get_stock_day(name, start='', end='', if_fq='qfq', type_='pd'):
  pass

    # def fetch_data():
    #     data = None
    #     try:
    #         time.sleep(0.002)
    #         pro = get_pro()
    #         data = ts.pro_bar(
    #             api=pro,
    #             ts_code=str(name),
    #             asset='E',
    #             adj=_get_subscription_type(if_fq),
    #             start_date=start,
    #             end_date=end,
    #             freq='D',
    #             factors=['tor',
    #                      'vr']
    #         ).sort_index()
    #         print('fetch done: ' + str(name))
    #     except Exception as e:
    #         print(e)
    #         print('except when fetch data of ' + str(name))
    #         time.sleep(1)
    #         data = fetch_data()
    #     return data

    # data = fetch_data()

    # data['date_stamp'] = data['trade_date'].apply(lambda x: cover_time(x))
    # data['code'] = data['ts_code'].apply(lambda x: str(x)[0:6])
    # data['fqtype'] = if_fq
    # if type_ in ['json']:
    #     data_json = QA_util_to_json_from_pandas(data)
    #     return data_json
    # elif type_ in ['pd', 'pandas', 'p']:
    #     data['date'] = pd.to_datetime(data['trade_date'], utc=False, format='%Y%m%d')
    #     data = data.set_index('date', drop=False)
    #     data['date'] = data['date'].apply(lambda x: str(x)[0:10])
    #     return data


def QA_fetch_get_stock_realtime():
    pass
    # data = ts.get_today_all()
    # data_json = QA_util_to_json_from_pandas(data)
    # return data_json


def QA_fetch_get_stock_info(name):
    pass
    # data = ts.get_stock_basics()
    # try:
    #     return data if name == '' else data.loc[name]
    # except:
    #     return None


def QA_fetch_get_stock_tick(name, date):
    pass
    # if (len(name) != 6):
    #     name = str(name)[0:6]
    # return ts.get_tick_data(name, date)


def QA_fetch_get_stock_list():
    df = QA_fetch_stock_basic()
    return list(df.ts_code)


def QA_fetch_get_stock_time_to_market():
    pass
    # data = ts.get_stock_basics()
    # return data[data['timeToMarket'] != 0]['timeToMarket']\
    #     .apply(lambda x: QA_util_date_int2str(x))


def QA_fetch_get_trade_date(end, exchange):
    pass
    # data = ts.trade_cal()
    # da = data[data.isOpen > 0]
    # data_json = QA_util_to_json_from_pandas(data)
    # message = []
    # for i in range(0, len(data_json) - 1, 1):
    #     date = data_json[i]['calendarDate']
    #     num = i + 1
    #     exchangeName = 'SSE'
    #     data_stamp = QA_util_date_stamp(date)
    #     mes = {
    #         'date': date,
    #         'num': num,
    #         'exchangeName': exchangeName,
    #         'date_stamp': data_stamp
    #     }
    #     message.append(mes)
    # return message


def QA_fetch_get_lhb(date):
    pass


def QA_fetch_get_stock_money():
    pass


def QA_fetch_get_stock_block():
    """Tushare的版块数据
    
    Returns:
        [type] -- [description]
    """
    import tushare as ts
    csindex500 = ts.get_zz500s()
    try:
        csindex500['blockname'] = '中证500'
        csindex500['source'] = 'tushare'
        csindex500['type'] = 'csindex'
        csindex500 = csindex500.drop(['date', 'name', 'weight'], axis=1)
        return csindex500.set_index('code', drop=False)
    except:
        return None

def QA_update_stock_basic():
    """
    本地化所有股票基本信息
    """
    coll = DATABASE.stock_basic
    coll.create_index(
        [("code", ASCENDING), ("status", ASCENDING),
         ("list_date_stamp", ASCENDING)],
        unique=True,
    )

    # 初始化数据接口
    # pro = get_pro()
    # 获取所有数据
    # df_1 = pro.stock_basic(exchange="", list_status="L") 
    # df_2 = pro.stock_basic(exchange="", list_status="P")
    # df_3 = pro.stock_basic(exchange="", list_status="D")
    # df_1["status"] = "L"
    # df_2["status"] = "P"
    # df_3["status"] = "D"
    # df = df_1.append(df_2).append(df_3)

    df = QA_get_stock_basic()
    df["status"] = "L"
    df["code"] = QA_fmt_code_list(df.code)
    df["list_date_stamp"] = df.list_date.apply(QA_util_date_stamp)
    df = df.where(pd.notnull(df), None)
    js = QA_util_to_json_from_pandas(df)
    for item in js:
        qry = {
            "code": item["code"],
            "status": item["status"],
            "list_date_stamp": item["list_date_stamp"],
        }
        if coll.count_documents(qry) == 0:  # 增量更新
            coll.insert_one(item)


def QA_update_industry(
    level: Union[str, List, Tuple] = ["L1", "L2", "L3"],
    src: Union[str, List, Tuple] = "SW",
):
    """
    保存个股行业信息
    """
    # pro = get_pro()
    if isinstance(level, str):
        level = [level]
    if isinstance(src, str):
        src = [src]
    df_industry = pd.DataFrame()
    for s in src:
        for lv in level:
            try:
                if lv == "L1":
                  df_tmp = ak.sw_index_first_info()
                elif lv == "L2":
                  df_tmp = ak.sw_index_second_info()
                elif lv == "L3":
                  df_tmp = ak.sw_index_third_info()
                df_tmp["src"] = "sw"
                df_tmp["level"] = lv
                df_industry = pd.concat([df_industry, df_tmp])
            except Exception as e1:
                print(e1)
                time.sleep(61)
                if lv == "L1":
                  df_tmp = ak.sw_index_first_info()
                elif lv == "L2":
                  df_tmp = ak.sw_index_second_info()
                elif lv == "L3":
                  df_tmp = ak.sw_index_third_info()
                df_tmp["src"] = "sw"
                df_tmp["level"] = lv
                df_industry = pd.concat([df_industry, df_tmp])
    
    df_industry.columns = ["index_code", "industry_name", "num_stocks", "PE", "PE(TTM)", "PB", "dividened", "src", "level"]

    df_results = pd.DataFrame()
    for idx, item in df_industry.iterrows():
        if idx % 100 == 0:
            print(f"currently saving {idx}th record")
        try:
            df_tmp = ak.sw_index_third_cons(item["index_code"])
            df_tmp["industry_name"] = item["industry_name"]
            df_tmp["level"] = item["level"].lower()
            df_tmp["src"] = item["src"].lower()
            df_tmp = df_tmp.rename(columns={"股票代码": "con_code", "纳入时间": "in_date"})
            df_results = pd.concat([df_results, df_tmp], axis = 0)
        except Exception as e1:
            print(e1)
            time.sleep(61)
            try:
                df_tmp = ak.sw_index_third_cons(item["index_code"])
                df_tmp["industry_name"] = item["industry_name"]
                df_tmp["level"] = item["level"].lower()
                df_tmp["src"] = item["src"].lower()
                df_tmp = df_tmp.rename(columns={"股票代码": "con_code", "纳入时间": "in_date"})
                df_results = pd.concat([df_results, df_tmp], axis = 0)
            except Exception as e2:
                raise ValueError(e2)
    df_results.con_code = QA_fmt_code_list(df_results.con_code)
    df_results = df_results.rename(columns={"con_code": "code", "股票简称": "name", "申万1级":"SW_1", "申万2级":"SW_2", "申万3级":"SW_3", "价格":"price",
     "市盈率":"PE", "市盈率ttm":"PE(TTM)", "股息率":"dividend_rate", "市值":"market_value",
    "归母净利润同比增长(09-30)":"profit_increase_ratio(09-30)",
    "归母净利润同比增长(06-30)":"profit_increase_ratio(06-30)",
    "营业收入同比增长(09-30)":"revenue_increase_ratio(09-30)",
    "营业收入同比增长(06-30)":"revenue_increase_ratio(06-30)"})
    df_results = df_results.sort_values(by="code")
    df_results['out_date'] = False
    coll = DATABASE.industry
    coll.create_index(
        [
            ("code", ASCENDING),
            ("level", ASCENDING),
            ("src", ASCENDING),
            ("in_date_stamp", DESCENDING),
            ("out_date_stamp", DESCENDING),
        ],
        unique=False,
    )
    for item in QA_util_to_json_from_pandas(df_results):
        item["in_date_stamp"] = QA_util_date_stamp(item["in_date"])
        if not item["out_date"]:
            item["out_date_stamp"] = 9999999999
            item["out_date"] = 9999999999
        else:
            item["out_date_stamp"] = QA_util_date_stamp(item["out_date_stamp"])
        coll.update_one(
            {
                "code": item["code"],
                "level": item["level"],
                "src": item["src"],
                "in_date_stamp": item["in_date_stamp"],
            },
            {"$set": item},
            upsert=True,
        )
    print('finished saving industry')


# test

# print(get_stock_day("000001",'2001-01-01','2010-01-01'))
# print(get_stock_tick("000001.SZ","2017-02-21"))
if __name__ == '__main__':
    df = QA_get_stock_basic()
    # df = QA_fetch_get_stock_list()
    print(df)
