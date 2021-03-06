#!/usr/bin/env python
import rospy
import string
import time
import robot_obstacle
import robot_job
import robot_correction
import robot_publisher
import robot_listener
import robot_drive
import robot_move
import robot_turn
import robot_configure
import execute_command    #only here to init command buffer
from std_msgs.msg import String
from geometry_msgs.msg import Vector3
from serial_handler.msg import Status   #getting the msg file from the serial_handler package
from serial_handler.msg import Encoder
from serial_handler.msg import Sonar
# from gps_common.msg import GPSFix
from navigation_nova_bank.srv import *

time_aft_obs		= 0
time_start_obs		= 0

# The main progream process the robot logic
def main_commander():
	global time_aft_obs, time_start_obs
	# ----------------------------------------------------------------------------------------#
	#  If robot is on burn mode, it does not receive any encoder data                 		  #
	#  If robot is eanbled or received command to off the burn mode, the robot shall 		  #
	#   exit from burn mode and enter normal working mode                                     #
	# ----------------------------------------------------------------------------------------#
	if robot_drive.burn_mode:
		if not robot_drive.robot_enabled or robot_drive.burn_mode_desired:
			rospy.loginfo("Robot is on burn mode and robot disabled")
			time.sleep(0.1)
			return
		elif robot_drive.robot_enabled and robot_drive.burn_mode_desired:
			rospy.loginfo("Robot enabled, raised requiremnt to exit from burn mode")
			robot_drive.burn_mode_desired = False
			return;
		elif not robot_drive.burn_mode_desired:
			rospy.loginfo("Robot burn mode is on, received command to off burn mode")
			robot_drive.change_mode()
			time.sleep(1)
			return;

	# rospy.loginfo("testing")
	# publish running parameters to the para topic once the robot is not on burn mode
	robot_publisher.publish_parameters()

	# Very important error handling:
	# If Not any new data comming, waiting for next data,
	# if waiting too long need to issue warning or errorburn_mode_desired
	#rospy.loginfo("1")
	if(robot_listener.encoder_received == robot_listener.encoder_processed): 	#aaron comment
		robot_listener.process_encoder_delay() 									#aaron comment
		return 																	#aaron comment

	#rospy.loginfo("testing 2")

	# It process all the encoder data received - regardless robot status etc .
	#Including dynamically update robot GPS etc
	robot_listener.process_encoder_data() 										#aaron comment

	# Received command to switch to burn mode
	if robot_drive.burn_mode_desired:
		robot_job.pause_robot()
		robot_drive.change_mode()
		time.sleep(0.1)
		return


	#rospy.loginfo("testing 3")

	# Received command to on/off obstacle avoidance mode
	if robot_drive.obstacle_mode != robot_drive.obstacle_mode_desired:
		#robot_job.pause_robot()
		robot_drive.change_obstacle_mode()
		time.sleep(0.1)
		return

	# if remote control is on

	#rospy.loginfo("testing %d", robot_job.summon_mode)

	if robot_drive.manual_mode:
		rospy.loginfo("Robot is unde manual remote control, bearing: %f", robot_drive.bearing_now)
		time.sleep(0.1)
		return

	# ----------------------------------------------------------------------------------------#
	#  code to disable robot when required (clear all tasks)                    			  #
	# ----------------------------------------------------------------------------------------#
	# If robot not enabled, just need to disable the robot
	if not robot_drive.robot_enabled:
		#rospy.loginfo("Robot is disabled")
		robot_job.disable_robot()
		#rospy.loginfo("Disabled robot")
		time.sleep(0.1)
		return
		
	# rospy.logerr("Correction count: %d", robot_correction.correction_count)
	# ----------------------------------------------------------------------------------------#
	#  Codes for obstacle avoidence handling                     							  #
	# ----------------------------------------------------------------------------------------#
	# The flag would be set by hardware, we cannot do anything but blankly calculate the gps coordinates
	if robot_obstacle.robot_on_obstacle:
		robot_obstacle.resume_from_obstacle = False
		rospy.loginfo("Robot on obstacle avoidence, please wait")
		if time_start_obs <= time_aft_obs:
			time_start_obs = rospy.get_time()
			if time_start_obs - time_aft_obs > 15.0: #if obstacle avoidance mode is triggered within 5s, count +1
				robot_correction.correction_count = 0
		time.sleep(0.1)
		return

	# Robot obstancle avoidence is over, now resume to normal operation
	if robot_obstacle.robot_over_obstacle:
		rospy.logerr("Finished %d obstacle avoidance", robot_correction.correction_count)
		rospy.loginfo("Robot over obstacle")
		robot_obstacle.complete_obstacle_avoidance()
		time_aft_obs = rospy.get_time()
		time.sleep(0.1)
		return

	# First time button pressed, enter interaction mode
	if robot_drive.interaction_mode:
		rospy.loginfo("Robot interaction button pressed")
		if not robot_drive.robot_interacting:
			# pause the current tasks
			robot_job.pause_robot()
			# Start video chat
			robot_publisher.publish_chat()
			# Turn off the obstacle avoidance mode
			robot_drive.obstacle_mode_desired 	= False
			robot_drive.robot_paused		  	= True
			robot_drive.robot_interacting 	 	= True
			# send a command to call the office
			time.sleep(0.1)
			return;
		else:
			robot_drive.robot_paused		  	= False
			robot_drive.robot_interacting		= False
			robot_drive.obstacle_mode_desired 	= True


	# if video chat closed by any sides (server or robot), then to resume the robot for the job

	#rospy.loginfo("Process job 1") 
	# handle robot paused conidtions
	if robot_drive.robot_paused:
		rospy.loginfo("Pause robot")
		robot_job.pause_robot()

		if robot_job.summon_mode:
			robot_job.clear_job_list()
                	robot_job.prepare_to_panel()
			robot_drive.robot_paused = False
			robot_job.summon_mode = False
			robot_drive.robot_on_mission = False
		if robot_job.back_to_base_mode:
			robot_job.clear_job_list()
			robot_job.prepare_back_to_base()
			robot_drive.robot_paused = False
			robot_job.back_to_base_mode = False
			robot_drive.robot_on_mission = False
		if robot_drive.new_command: 
			robot_drive.robot_paused = False
			robot_drive.robot_on_mission = False
			robot_drive.new_command = False
		time.sleep(0.1)
		return;
	#rospy.loginfo("test 5")
	# Handle the low battery
	if robot_job.back_to_base_mode:
		rospy.loginfo('Back to base mode')
		robot_drive.robot_paused = True
		#robot_job.clear_job_list()
		# Generate jobs which can drive robot back to base
		#robot_job.prepare_back_to_base()
		return

	if robot_job.summon_mode:
		rospy.loginfo('summon mode')
		robot_drive.robot_paused = True 
		#robot_job.clear_job_list()
		#robot_job.prepare_to_panel()
		return 

	#rospy.loginfo("test 6");
	# ----------------------------------------------------------------------------------------#
	#  Codes for robot normal jobs like walking and turning       							  #
	# ----------------------------------------------------------------------------------------#
	# Check whether if there's any job left for the robot
	# If no jobs, make sure robot stopped moving, we cannot leave robot moving there
	if not robot_job.has_jobs_left():
		if not robot_drive.obstacle_mode_desired: 
			robot_drive.obstacle_mode_desired = False
			return

		robot_job.process_no_job()
		if robot_job.back_to_base_mode:
			robot_job.back_to_base_mode = False 
		if robot_job.summon_mode:
			robot_job.summon_mode = False 
		# rospy.loginfo("Complete all jobs")
		time.sleep(0.1)
		return


	#robot_drive.obstacle_mode_desired = True #abc
	#rospy.loginfo("Process job")
	job_completed = robot_job.process_job()
	#rospy.loginfo("Process job1")
	# ----------------------------------------------------------------------------------------#
	#  Robot's doing the initialization jobs, not normal jobs      							  #
	# ----------------------------------------------------------------------------------------#
	#if not robot_drive.robot_initialized:
	#	robot_job.complete_init_compass(compass_data[compass_index])
	#	return

	# ----------------------------------------------------------------------------------------#
	#  Error compensation after current job completed      									  #
	# ----------------------------------------------------------------------------------------#
	if job_completed:
		# no_correction_jobs = robot_job.no_correction_jobs()
		rospy.logerr("%f", robot_drive.bearing_now)
		job_executed = robot_job.current_job()
		robot_job.complete_current_job()
		# rospy.logerr(robot_move.move_amend)
		if robot_move.move_amend or robot_turn.turn_amend: # or (not robot_job.has_jobs_left()):
			robot_job.amend_regular_jobs(job_executed, 'C', 2*robot_correction.min_correction_distance)
			robot_move.move_amend = False
			robot_turn.turn_amend = False

		# if no_correction_jobs == 0:
		# 	rospy.loginfo("Complete a normal job, check whether correction is needed")
		# 	robot_correction.dist_correction_normal()
		# elif no_correction_jobs == 1: # the job is last correction job
		# 	rospy.loginfo("Complete all correction jobs, check whether further correction is needed")
		# 	robot_correction.dist_correction_correction();

def get_ip_service():
	s = rospy.Service('get_ip', GetIP, robot_configure.handle_get_ip)

#subscribes to different topic
def main_listener():
	rospy.init_node('commander')

	# Step 1:
	# Regiser callback to recived data from different nodes which would be used for calculation
	#rospy.Subscriber('compass', String, robot_listener.compass_callback) 			#aaron comment
	rospy.Subscriber('encoder', Encoder, robot_listener.serial_encoder_callback) 			#aaron comment
	rospy.Subscriber('keyboard', String, robot_listener.keyboard_callback)
	#rospy.Subscriber('rc_sensor_f', String, robot_listener.rc_sensor_f_callback)  #write the callbacks properly
	#rospy.Subscriber('rc_sensor_b', String, robot_listener.rc_sensor_b_callback)  #once we can get the correct data formats
	#ADD SUBSCRIBERS FOR GYRO DATA, MAKE CALLBACKS TO HANDLE THEM
	#@yuqing_obstacledriverread
	#rospy.Subscriber('obstacle_status', String, robot_listener.obstacle_status_callback) #was previously driver_obstacle
	rospy.Subscriber('job', String, robot_listener.job_callback)
	rospy.Subscriber('chat', String, robot_listener.chat_callback)
	rospy.Subscriber('control', String, robot_listener.control_callback)
	#rospy.Subscriber('velocity', Vector3, robot_listener.velocity_callback)
	rospy.Subscriber('IMU', Vector3, robot_listener.IMU_callback) #not yet done
	rospy.Subscriber('hardware_status', Status, robot_listener.status_callback)
	rospy.Subscriber('face_detection', String, robot_listener.face_detection_callback)
	rospy.Subscriber('bluetooth', String, robot_listener.bluetooth_callback)
	rospy.Subscriber('summon_robot', String, robot_listener.panel_summon_callback)
	# rospy.Subscriber('extended_fix', GPSFix, robot_listener.gps_callback)
	rospy.Subscriber('pose_aft_pf', Vector3, robot_listener.pose_pf_callback)


	time_aft_obs = rospy.get_time()
	time_start_obs = rospy.get_time()
	# Provide a service for getting ip of wireless network 
	get_ip_service()
	# Step 2:
	# Start the main loop

	while not rospy.is_shutdown():
		main_commander()
	rospy.spin()

if __name__ == '__main__':
	try:
		# AAron's initial one for final testing
		#job_generator(initial_bearing, loops)
		robot_configure.read_system_config()
		robot_correction.init_gps()
		robot_listener.init_encoder_buffer()
		robot_listener.init_compass_buffer()
		main_listener()
	except rospy.ROSInterruptException:
		pass
