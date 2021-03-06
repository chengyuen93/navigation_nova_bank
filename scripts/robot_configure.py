#!/usr/bin/env python
import socket
import fcntl
import struct
import rospy
import string
import ConfigParser
import os
import robot_configure
import robot_drive
import robot_job
import robot_turn
import robot_move
import robot_correction
import robot_listener
import coordTransform_utils

from std_msgs.msg import String

def read_config(config_file_path, field, key):
    cf = ConfigParser.ConfigParser()
    ret = True
    result = None
    try:
        cf.read(config_file_path)
        result = cf.get(field, key)
    except:
    	ret = False
        rospy.loginfo("Failed to read %s-%s", field, key)
    return ret, result

def read_config_float(config_file_path, field, key):
    cf = ConfigParser.ConfigParser()
    ret = True
    val = 0
    try:
        cf.read(config_file_path)
        result = cf.get(field, key)
        val = float(result)
    except:
        ret = False
        rospy.loginfo("Failed to read %s-%s", field, key)
    return ret, val

def write_config(config_file_path, field, key, value):
    cf = ConfigParser.ConfigParser()
    ret = True
    try:
        cf.read(config_file_path)
        cf.set(field, key, value)
        cf.write(open(config_file_path,'w'))
    except:
    	ret = False
        rospy.loginfo("Failed to write parameters")
    return ret

def handle_get_ip(req):
    return robot_configure.get_ip_address('wlan0')

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
)[20:24])


def read_system_config():
    # Read configure path
    print("Read configuration file")
    config_path = os.path.dirname(os.path.abspath(__file__)) + '/robot.cfg'
    size_para   = 34
    ret         = [None] * size_para

    # Now reading configurable parameters
    # [tuning parameters] related
    ret[0], robot_drive.linear_encode_to_mm             = read_config_float(config_path, 'tuning', 'linear_encode_to_mm')
    ret[1], robot_drive.turning_encode_to_mm            = read_config_float(config_path, 'tuning', 'turning_encode_to_mm')
    ret[2], robot_drive.dist_param                      = read_config_float(config_path, 'tuning', 'dist_param')
    ret[3], robot_drive.angle_param                     = read_config_float(config_path, 'tuning', 'angle_param')
    # [mechanical related]
    ret[4], robot_drive.turn_radius                     = read_config_float(config_path, 'mechanic', 'turn_radius')
    # [correction]
    ret[5], robot_correction.min_correction_distance    = read_config_float(config_path, 'correction', 'min_correction_distance')
    ret[6], robot_correction.min_correction_angle       = read_config_float(config_path, 'correction', 'min_correction_angle')
    ret[7], robot_correction.max_correction_run         = read_config_float(config_path, 'correction', 'max_correction_runs')
    # [move]
    ret[8], robot_move.dist_to_correct                  = read_config_float(config_path, 'move', 'dist_to_correct')
    ret[9], robot_move.dist_lower_speed                 = read_config_float(config_path, 'move', 'dist_lower_speed')
    ret[10], robot_move.dist_lowest_speed                = read_config_float(config_path, 'move', 'dist_lowest_speed')
    ret[11], robot_move.linear_full_speed               = read_config_float(config_path, 'move', 'linear_full_speed')
    ret[12], robot_move.linear_lower_speed              = read_config_float(config_path, 'move', 'linear_lower_speed')
    ret[13], robot_move.linear_lowest_speed             = read_config_float(config_path, 'move', 'linear_lowest_speed')
    # [turn]
    ret[14], robot_turn.angle_lower_speed               = read_config_float(config_path, 'turn', 'angle_lower_speed')
    ret[15], robot_turn.angle_lowest_speed              = read_config_float(config_path, 'turn', 'angle_lowest_speed')
    ret[16], robot_turn.turn_full_speed                 = read_config_float(config_path, 'turn', 'turn_full_speed')
    ret[17], robot_turn.turn_lower_speed                = read_config_float(config_path, 'turn', 'turn_lower_speed')
    ret[18], robot_turn.turn_lowest_speed               = read_config_float(config_path, 'turn', 'turn_lowest_speed')
    ret[19], robot_drive.bank_radius                     = read_config_float(config_path, 'turn', 'bank_radius')
    ret[20], robot_drive.min_bank_dist                   = read_config_float(config_path, 'turn', 'min_bank_dist')
    # [init]
    ret[21], robot_drive.obstacle_mode                  = read_config_float(config_path, 'init', 'obstacle_mode')
    ret[22], robot_drive.robot_enabled                  = read_config_float(config_path, 'init', 'robot_enabled')
    ret[23], robot_drive.robot_paused                   = read_config_float(config_path, 'init', 'robot_paused')
    ret[24], init_lon                                 	= read_config_float(config_path, 'init', 'init_lon')
    ret[25], init_lat                               	= read_config_float(config_path, 'init', 'init_lat')
    ret[26], robot_job.init_bearing                     = read_config_float(config_path, 'init', 'init_bearing')
    ret[27], robot_correction.balance_left_right        = read_config_float(config_path, 'init', 'balance_left_right')
    #[mode]
    ret[28], robot_correction.odom_mode                 = read_config_float(config_path, 'mode', 'odom_mode')
    ret[29], robot_listener.imu_mode                    = read_config_float(config_path, 'mode', 'IMU_mode')
    ret[30], robot_listener.gps_mode                    = read_config_float(config_path, 'mode', 'GPS_mode')
    ret[31], robot_correction.follow_map_gps            = read_config_float(config_path, 'mode', 'follow_map_gps')
    ret[32], robot_correction.map_wgs84                 = read_config_float(config_path, 'mode', 'map_wgs84')
    ret[33], robot_correction.indoor_coord              = read_config_float(config_path, 'mode', 'indoor_coord')

#-------------------------------------------------------------------------------------------------------------------------------------------chengyuen11/10
    if not robot_correction.map_wgs84 and not robot_correction.follow_map_gps:
        lonlat = coordTransform_utils.gcj02_to_wgs84(init_lon, init_lat)
        robot_job.init_lon = lonlat[0]
        robot_job.init_lat = lonlat[1]
    else:
        robot_job.init_lon = init_lon
        robot_job.init_lat = init_lat
#-------------------------------------------------------------------------------------------------------------------------------------------

    # check whether the reading is successful or not
    for index in range(size_para):
        if not ret[index]:
            print("The ",index,"parameter is not correct")

    print("Finished read configure file")
    return
