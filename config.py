from easydict import EasyDict as edict


cfg = edict()

# 数据库（系统表出勤表）
cfg.mongodb = edict()
cfg.mongodb.ip = 'localhost:27017'
cfg.mongodb.db_name = 'Workers_attendance_system'
cfg.mongodb.table_workers_information = 'workers_information'
cfg.mongodb.table_attendances = 'workers_information_attendance'
cfg.mongodb.table_attendance_check_on_day = 'workers_attendance_check_on_day'
cfg.mongodb.table_dict_state= 'dict_attendance_state'
# 数据库（门禁系统的出勤表）
# cfg = edict()
cfg.mysql = edict()
cfg.mysql.host = '10.18.19.79'
cfg.mysql.user = 'root'
cfg.mysql.passwd = '123456'
cfg.mysql.db_name = 'counsykt'

# 考勤上班时间定义：
cfg.worktime = edict()
# 上班缓冲时间(时:分)
cfg.worktime.buffer = '0:10'
# 缺勤缓冲时间(时:分)
cfg.worktime.leave_buffer = '1:00'
# 上班时间定义(时:分)
cfg.worktime.sw_judge_time = '6:00'  # 系统考勤开始时间
cfg.worktime.sw_start_time = '08:30'  # 系统考勤上班时间
cfg.worktime.xw_end_time = '17:30'  # 系统考勤下班时间
cfg.worktime.sys_end = '23:59'  # 系统考勤结束时间
