# 第一步 基本信息表录入mongodb
import xlrd
from tqdm import tqdm
import pymongo
from work_attendance.config import cfg


def generate_workers_information():
    # 链接数据库
    myclient = pymongo.MongoClient(cfg.mongodb.ip)
    workers_bace_table = myclient[cfg.mongodb.db_name][cfg.mongodb.table_workers_information]
    workers_bace_table.drop()
    # 定义表单
    base_path = 'worker_bace_information.xlsx'
    xl = xlrd.open_workbook(base_path)
    table = xl.sheet_by_name('Sheet1')
    rows = table.nrows
    cols = table.ncols

    for row_num in tqdm(range(2, rows)):
        person_one_k_v = {}
        for col_num in range(cols):
            key = table.cell(0, col_num).value
            key_value = table.cell(row_num, col_num).value
            if key == 'post_no' or key == 'cell_phone':
                try:
                    key_value = str(int(key_value))
                except:
                    print('数据插入有问题！！')
            person_one_k_v[key] = key_value
        workers_bace_table.insert_one(person_one_k_v)


def generate_table_dict_state():
    myclient = pymongo.MongoClient(cfg.mongodb.ip)
    dict_state_table = myclient[cfg.mongodb.db_name][cfg.mongodb.table_dict_state]
    dict_state_table.drop()
    # 唯一标识、字段、状态符号、状态符号解释
    dict_state_table.insert_one(
        {'table_id': 0, 'field': 'in_state', 'field_chn': '上班状态', 'status_symbol': 0, 'interpretation': "正常"})
    dict_state_table.insert_one(
        {'table_id': 1, 'field': 'in_state', 'field_chn': '上班状态', 'status_symbol': 1, 'interpretation': "迟到"})
    dict_state_table.insert_one(
        {'table_id': 2, 'field': 'in_state', 'field_chn': '上班状态', 'status_symbol': 2, 'interpretation': "缺卡"})
    # --
    dict_state_table.insert_one(
        {'table_id': 3, 'field': 'out_state', 'field_chn': '下班状态', 'status_symbol': 0, 'interpretation': "正常"})
    dict_state_table.insert_one(
        {'table_id': 4, 'field': 'out_state', 'field_chn': '下班状态', 'status_symbol': 1, 'interpretation': "早退"})
    dict_state_table.insert_one(
        {'table_id': 5, 'field': 'out_state', 'field_chn': '下班状态', 'status_symbol': 2, 'interpretation': "缺卡"})
    # --
    dict_state_table.insert_one(
        {'table_id': 6, 'field': 'all_state', 'field_chn': '全天考勤状态', 'status_symbol': 0, 'interpretation': "正常"})
    dict_state_table.insert_one(
        {'table_id': 7, 'field': 'all_state', 'field_chn': '全天考勤状态', 'status_symbol': 1, 'interpretation': "有问题"})
    dict_state_table.insert_one(
        {'table_id': 8, 'field': 'all_state', 'field_chn': '全天考勤状态', 'status_symbol': 2, 'interpretation': "缺勤"})


# if __name__ == '__main__':
#     generate_workers_information()
#     generate_table_dict_state()
