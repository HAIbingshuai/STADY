import pymongo
import pymysql
from tqdm import tqdm
import time
from chinese_calendar import is_workday
from work_attendance.config import cfg
import datetime
from datetime import datetime, timedelta, date
from apscheduler.schedulers.blocking import BlockingScheduler

from work_attendance.worker_bace_insert_db.worker_bace_insert_in_progress import generate_workers_information, generate_table_dict_state


def getBetweenDay(begin_date, end_date):
    """
    两个日期（字符串）直接拿的所有日期
    :param begin_date:
    :param end_date:
    :return:
    """
    date_list = []
    begin_date = datetime.datetime.strptime(begin_date, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    while begin_date <= end_date:
        date_str = begin_date.strftime("%Y-%m-%d")
        date_list.append(date_str)
        begin_date += datetime.timedelta(days=1)
    return date_list


# 时分转分
def function_convert_time(time):
    sum_m = 0
    for i, one in enumerate(time.split(':')):
        sum_m = sum_m + 60 ** (1 - i) * int(one)
    return sum_m


# 分转时分
def function_convert_alltime(miao):
    M = int(miao % 60)
    H = int(miao // 60)
    str_time = str(H) + ':' + str(M)
    return str_time


def one_round_working_interval(time_list):
    # 所有考勤记录
    attendance_seconds = [function_convert_time(one) for one in time_list]
    attendance_seconds.sort(reverse=False)
    time_2 = cfg.worktime.sw_start_time
    time_5 = cfg.worktime.xw_end_time
    # 迟到点(上班点+缓冲点)
    late_1_time = function_convert_time(time_2) + function_convert_time(cfg.worktime.buffer)
    # 缺勤时间点(上班点+规定1小时时间)
    leave_1_time = function_convert_time(time_2) + function_convert_time(cfg.worktime.leave_buffer)
    # 缺勤时间点(下班点-规定1小时时间)
    leave_2_time = function_convert_time(time_5) - function_convert_time(cfg.worktime.leave_buffer)
    # 早退点(下班点-缓冲点)
    leave_3_time = function_convert_time(time_5) - function_convert_time(cfg.worktime.buffer)

    # is_in_operation_state 上班状态（0：正常、1：迟到、2、上班缺卡）
    # is_out_operation_state 下班状态（0：正常、1：早退、2、下班缺卡）
    # is_operation_all_state通勤状态（0：正常出勤、1：通勤有问题、2：缺勤）

    if len(attendance_seconds) == 0:
        is_in_operation_state = 2
        is_out_operation_state = 2
        is_operation_all_state = 2
        work_time_punch_in = ''
        work_time_punch_out = ''
    else:
        # 上班判断
        work_time_punch_in_temp_Minutes = attendance_seconds[0]
        work_time_punch_in = function_convert_alltime(work_time_punch_in_temp_Minutes)
        if work_time_punch_in_temp_Minutes < late_1_time:
            is_in_operation_state = 0
        elif work_time_punch_in_temp_Minutes < leave_1_time:
            is_in_operation_state = 1
        else:
            is_in_operation_state = 2

        # 下班判断
        work_time_punch_out_temp_Minutes = attendance_seconds[-1]
        work_time_punch_out = function_convert_alltime(work_time_punch_out_temp_Minutes)
        if work_time_punch_out_temp_Minutes > leave_3_time:
            is_out_operation_state = 0
        elif work_time_punch_out_temp_Minutes < leave_2_time:
            is_out_operation_state = 1
        else:
            is_out_operation_state = 2

        # 整体判断
        if is_in_operation_state == 0 and is_out_operation_state == 0:
            is_operation_all_state = 0
        elif is_in_operation_state == 2 and is_out_operation_state == 2:
            is_operation_all_state = 2
        else:
            is_operation_all_state = 1

    # 上班状态、上班时间
    content1 = [is_in_operation_state, work_time_punch_in]
    # 下班状态、下班时间
    content2 = [is_out_operation_state, work_time_punch_out]
    return is_operation_all_state, content1, content2


class System_attendance(object):
    # 考勤系统类：进行考勤处理
    def __init__(self):
        # 系统表
        self.workers_db = pymongo.MongoClient(cfg.mongodb.ip)[cfg.mongodb.db_name]
        self.table_workers_information = self.workers_db[cfg.mongodb.table_workers_information]
        self.table_attendances = self.workers_db[cfg.mongodb.table_attendances]
        self.table_attendance_check_on_day = self.workers_db[cfg.mongodb.table_attendance_check_on_day]
        # 门禁表
        self.conn = pymysql.connect(host=cfg.mysql.host, user=cfg.mysql.user, passwd=cfg.mysql.passwd)
        self.conn.select_db(cfg.mysql.db_name)

    def get_access_control_data_2_attendance(self, someday):
        """
        # 门禁数据读取到本地attendances(出勤表)
        :param somedays_num: 几天内的数据
        """
        data_someday = datetime.strptime(someday, "%Y-%m-%d").date()
        print(someday)
        person_all_k_v = []
        cur = self.conn.cursor()
        cur.execute(
            "select Name,CreateDateTime,DevLocation from swingcard where to_days(%s)-to_days(CreateDateTime) < 1",
            (data_someday,))
        while 1:
            res = cur.fetchone()
            if res is None:
                # 表示已经取完结果集
                break
            person_one_k_v_dict = {
                'name': res[0],
                'data': res[1].strftime('%Y-%m-%d'),
                'time': res[1].strftime('%H:%M'),
                'position': res[2],
                'data_source': 'access_control'
            }
            person_all_k_v.append(person_one_k_v_dict)
        cur.close()
        # 链接数据库
        for one_attendence in tqdm(person_all_k_v):
            is_have = self.table_attendances.count_documents(one_attendence)
            if is_have == 0:
                self.table_attendances.insert_one(one_attendence)

    def get_post_no_and_name(self):
        """
        员工基础表单获取人员工号、姓名列表字典表
        :param table_workers_information:
        :return: 人员工号、姓名列表
        """
        name_post_no_dict = {worker_bace['name']: worker_bace['post_no'] for worker_bace in
                             self.table_workers_information.find({})}
        return name_post_no_dict

    def get_attendancetimelist_by_data_and_name(self, worker_name, attendantce_time):
        """
        考勤系统中出勤表根据人名+时间，得到出勤信息
        :param worker_name: 人名
        :param attendantce_time: 时间
        :return:
        """
        myquery = {"name": worker_name, 'data': attendantce_time}
        workers_time_list = [worker_bace['time'] for worker_bace in self.table_attendances.find(myquery)]
        return workers_time_list

    def attendance_check_up_day(self, data_order_list):
        """
        计算两个时间间每一天的考勤记录，一天一条
        :param start_time: 开始的一天（年-月-日）
        :param end_time: 结束的一天（年-月-日）
        """

        post_no_and_name = self.get_post_no_and_name()
        # 去除非工作日
        data_order_list_workday = []
        for one in data_order_list:
            if is_workday(datetime.strptime(one, "%Y-%m-%d").date()):
                data_order_list_workday.append(one)

        # 统计计算
        for worker_name in self.get_post_no_and_name():
            for data_day in data_order_list_workday:
                time_attendance_list = self.get_attendancetimelist_by_data_and_name(worker_name, data_day)
                # 整体状态、[上班状态、上班时间]，[下班状态、下班时间]
                is_operation_all_state, content1, content2 = one_round_working_interval(time_attendance_list)

                # 先删除这天的库里记录（保证每天每人只有一条数据）
                self.table_attendance_check_on_day.remove(
                    {'post_no': post_no_and_name[worker_name], 'time_today': data_day})
                one_e_dict = {
                    'post_no': post_no_and_name[worker_name],
                    'name': worker_name,
                    'time_today': data_day,
                    # 状态
                    'attendance_state': is_operation_all_state,
                    # 上班状态
                    'state_in': content1[0],
                    # 下班状态
                    'state_out': content2[0],
                    # 上班时间点
                    'punch_in': content1[1],
                    # 下班时间点
                    'punch_out': content2[1],
                    'updata_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                }
                self.table_attendance_check_on_day.insert_one(one_e_dict)

    # 定时任务开始：
    def timed_task_by_data_list(self, day_start, day_end):
        cur = self.conn.cursor()
        # 1门禁系统生成数据导入考勤系统的出勤表中
        data_order_list = getBetweenDay(day_start, day_end)
        for one_day in data_order_list:
            self.get_access_control_data_2_attendance(one_day)
        # 2考勤系统的出勤表计算得到考勤系统的考勤表
        self.attendance_check_up_day(data_order_list)
        cur.close()
        # self.conn.commit()
        # self.conn.close()

    # 定时任务开始：
    def timed_task_by_data_one(self, day_time):
        cur = self.conn.cursor()
        # 1门禁系统生成数据导入考勤系统的出勤表中
        self.get_access_control_data_2_attendance(day_time)
        # 2考勤系统的出勤表计算得到考勤系统的考勤表
        self.attendance_check_up_day([day_time])
        cur.close()


def timed_task():
    # 第一次使用可以
    # 基本信息表更新
    # 计出字典表更新
    generate_workers_information()
    generate_table_dict_state()

    today_string = date.today().strftime('%Y-%m-%d')
    yestday_string = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(today_string + '日凌晨出' + yestday_string + '勤数据考勤统计开始...')
    att = System_attendance()
    att.timed_task_by_data_one(yestday_string)
    del att


if __name__ == '__main__':
    scheduler = BlockingScheduler()
    print('定时任务启动...')
    scheduler.add_job(timed_task, 'cron', day_of_week="0-6", hour=10, minute=33, misfire_grace_time=120)
    scheduler.start()
