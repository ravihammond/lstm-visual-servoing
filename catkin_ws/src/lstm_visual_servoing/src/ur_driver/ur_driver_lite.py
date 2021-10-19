#!/usr/bin/env python3

# http://wiki.ros.org/ROS/Tutorials/WritingPublisherSubscriber%28python%29

import rospy
import threading
import socket
import time
import math
import ur_rtde
import os

import geometry_msgs.msg
import std_msgs.msg
import pyquaternion  # pip install pyquaternion # http://kieranwynn.github.io/pyquaternion

import tf

class Driver():
    """The Driver class does a couple of things:
    1:  It sets up a few ros publishers that constantly publish some information
        from the robot. It uses the the Real Time Data Exchange (rtde) to get
        data from the robot then uses a seperate publishing thread to publish it
        on ROS topics
    2:  It constantly tries to ensure that the robot is running the correct ur script.
        For the driver to work, the robot needs to be running a custom ur script
        that communicates with the driver. The program loop checks if there is a
        healthy heartbeat between the robot and the driver. If the heartbeat is
        unhealthy the ur script is continuously send to the robot.
    3:  It subscribes to a heap of movement and gripper topics. When it
        receives messages it will move the robot respectively."""


    class Registers():
        """ This sub class just contains a heap of constants that describe what
            rtde registers have been used for"""

        X = "input_double_register_0"
        Y = "input_double_register_1"
        Z = "input_double_register_2"
        RX = "input_double_register_3"
        RY = "input_double_register_4"
        RZ = "input_double_register_5"

        GRIPPER_POS_INPUT = "input_double_register_6"
        GRIPPER_SPEED_INPUT = "input_double_register_7"
        GRIPPER_FORCE_INPUT = "input_double_register_8"

        GRIPPER_POS_OUTPUT = "output_double_register_0"
        GRIPPER_OBJ_DETECTED_OUTPUT = "output_int_register_3"

        HEARTBEAT_INPUT = "input_int_register_0"
        HEARTBEAT_OUTPUT = "output_int_register_0"

        MOVEMENT_COUNTER_INPUT = "input_int_register_1"
        MOVEMENT_COUNTER_OUTPUT = "output_int_register_1"

        GRIPPER_COUNTER_INPUT = "input_int_register_2"
        GRIPPER_COUNTER_OUTPUT = "output_int_register_2"

        MOVEMENT_TYPE = "input_int_register_3"

    def __init__(self,robot_ip_address):
        self.robot_ip_address = robot_ip_address
        self.alive = True
        self.publish_loop_thread = threading.Thread(target=self.__publish_loop, name="Publish Thread")
        self.program_loop_thread = threading.Thread(target=self.__program_loop, name="Program Thread")
        self.real_time_data_exchange = ur_rtde.UrRealTimeDataExchange(robot_ip_address)


        self.movement_counter = 0
        self.gripper_counter = 0

    def __enter__(self):
        print("ur_driver_lite enter called")


        rospy.init_node("ur_driver_lite")
        rospy.Subscriber("move_to_pose",geometry_msgs.msg.Transform,self.__move_to_pose_callback)
        rospy.Subscriber("servo_to_pose",geometry_msgs.msg.Transform,self.__servo_to_pose_callback)
        rospy.Subscriber("move_at_speed",geometry_msgs.msg.Twist,self.__move_at_speed_callback)
        rospy.Subscriber("move_gripper_to_pos",std_msgs.msg.Float32,self.__gripper_pos_callback)


        self.tcp_force_pub = rospy.Publisher("tcp_wrench",geometry_msgs.msg.Wrench,queue_size=10)
        self.joint_angle_pub = rospy.Publisher("joint_angle",std_msgs.msg.Float32MultiArray,queue_size=10)

        self.gripper_pos_pub = rospy.Publisher("gripper_pos",std_msgs.msg.Float32,queue_size=10)
        self.gripper_obj_detected_pub = rospy.Publisher("gripper_obj_detected",std_msgs.msg.Bool,queue_size=10)

        self.real_time_data_exchange.__enter__()
        self.publish_loop_thread.start()
        self.program_loop_thread.start()

        print("ur_driver_lite enter complete")
        return self

    def __exit__(self,*args):
        print("exit called")
        self.alive = False
        self.publish_loop_thread.join()
        self.program_loop_thread.join()
        self.real_time_data_exchange.__exit__(args)
        print("exit complete")

    def __publish_loop(self):
        """
        The publish loop should be called from another thread. It will run
        continuously to get data from the real time data exchange and publish it
        on ros
        """

        #instanciate transform broadcaster so that we can broadcast tcp and
        #camera position
        br = tf.TransformBroadcaster()

        #publish while alive
        while self.alive:

            #create a dict of the variables we want to read from the rtde
            output_data = {
                "actual_TCP_pose":None,
                "actual_TCP_force":None,
                Driver.Registers.GRIPPER_POS_OUTPUT:None,
                Driver.Registers.GRIPPER_OBJ_DETECTED_OUTPUT:None,
                "actual_q":None
                }

            #read the data from the rtde into our dict
            self.real_time_data_exchange.get_output_data(output_data)

            #Get tcp pose in the form [x,y,z,rx,ry,rz]. Note rotation uses axis angle
            tcp_pose = output_data["actual_TCP_pose"]

            #get the translations as [x,y,z]
            t = tcp_pose[0:3]

            #The rotation angle is the length of the vector [rx,ry,rz]. Pythagoras yo
            angle = math.sqrt( tcp_pose[3]**2 + tcp_pose[4]**2 + tcp_pose[5]**2 )

            #create ros quaternion from angle and axis
            q = tf.transformations.quaternion_about_axis(angle,tcp_pose[3:6])

            #publish robot tool center point with respect to robot base
            br.sendTransform(t,q,rospy.Time.now(),"ur_tcp","base")

            #
            q1 = tf.transformations.quaternion_about_axis(90/180.0*math.pi,(0,0,1))
            q2 = tf.transformations.quaternion_about_axis(-104/180.0*math.pi,(0,1,0))
            q3 = tf.transformations.quaternion_multiply(q1,q2)
            br.sendTransform((0.0,-0.065,0.04),q3,rospy.Time.now(),"camera_link","ur_tcp",)

            # publish robot gripper:
            br.sendTransform((0.0,0.0,0.2485),(0,0,0,1),rospy.Time.now(),"gripper_point","ur_tcp",)

            #publish the robots force and torque
            fx,fy,fz,tx,ty,tz = output_data["actual_TCP_force"]
            force = geometry_msgs.msg.Vector3(fx,fy,fz)
            torque = geometry_msgs.msg.Vector3(tx,ty,tz)
            wrench_msg = geometry_msgs.msg.Wrench(force,torque)
            self.tcp_force_pub.publish(wrench_msg)

            #publish the joint angles (actual q)
            actualQ = output_data["actual_q"]
            jointAngles = std_msgs.msg.Float32MultiArray(data=actualQ)
            self.joint_angle_pub.publish(jointAngles)


            #publish gripper feedback
            self.gripper_pos_pub.publish( output_data[Driver.Registers.GRIPPER_POS_OUTPUT] )
            self.gripper_obj_detected_pub.publish( output_data[Driver.Registers.GRIPPER_OBJ_DETECTED_OUTPUT] )

            #print(output_data["actual_TCP_force"])
            time.sleep(0.01)


    def __program_loop(self):
        while self.alive:
            try:

                self.secondary_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                #self.secondary_client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)#not sure if this is needed by just copied this
                #self.secondary_client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)#not sure if this is needed by just copied this
                self.secondary_client_socket.settimeout(1)
                self.secondary_client_socket.connect((self.robot_ip_address, 30002))

                dir_path = os.path.dirname(os.path.realpath(__file__)) + "/robot_ur_script"
                with open(dir_path, "rb") as f:
                    script = f.read()

                while self.alive:
                    self.secondary_client_socket.sendall(script)

                    last_time = time.time()
                    inputs = {Driver.Registers.HEARTBEAT_INPUT:0}
                    outputs = {Driver.Registers.HEARTBEAT_OUTPUT:0}

                    while self.alive:
                        self.real_time_data_exchange.set_input_data(inputs)
                        self.real_time_data_exchange.get_output_data(outputs)

                        if inputs[Driver.Registers.HEARTBEAT_INPUT] == outputs[Driver.Registers.HEARTBEAT_OUTPUT]:
                            inputs[Driver.Registers.HEARTBEAT_INPUT] += 1
                            last_time = time.time()


                        if time.time() - last_time > 2.0:
                            print("Program watchdog timeout")
                            break
                        time.sleep(0.1)
                self.secondary_client_socket.sendall("speedj([0,0,0,0,0,0],a=1.0)\n")


            except (OSError,socket.timeout,socket.error) as e:
                time.sleep(0.5)

            except Exception as e:
                self.alive = False
                raise e

            finally:
                pass

    def __move_to_pose_callback(self,data):
        t = data.translation
        r = data.rotation

        q = pyquaternion.Quaternion(r.w,r.x,r.y,r.z)

        axis_angle = q.axis
        axis_angle[0] *= q.radians
        axis_angle[1] *= q.radians
        axis_angle[2] *= q.radians

        self.movement_counter += 1

        input_dict = {
        Driver.Registers.X: t.x,
        Driver.Registers.Y: t.y,
        Driver.Registers.Z: t.z,
        Driver.Registers.RX: axis_angle[0],
        Driver.Registers.RY: axis_angle[1],
        Driver.Registers.RZ: axis_angle[2],
        Driver.Registers.MOVEMENT_TYPE   : 1, #movment type
        Driver.Registers.MOVEMENT_COUNTER_INPUT   : self.movement_counter
        }

        self.real_time_data_exchange.set_input_data(input_dict)

    def __servo_to_pose_callback(self,data):
        t = data.translation
        r = data.rotation

        q = pyquaternion.Quaternion(r.w,r.x,r.y,r.z)

        axis_angle = q.axis
        axis_angle[0] *= q.radians
        axis_angle[1] *= q.radians
        axis_angle[2] *= q.radians

        self.movement_counter += 1

        input_dict = {
        Driver.Registers.X: t.x,
        Driver.Registers.Y: t.y,
        Driver.Registers.Z: t.z,
        Driver.Registers.RX: axis_angle[0],
        Driver.Registers.RY: axis_angle[1],
        Driver.Registers.RZ: axis_angle[2],
        Driver.Registers.MOVEMENT_TYPE   : 2, #movment type
        Driver.Registers.MOVEMENT_COUNTER_INPUT   : self.movement_counter
        }

        self.real_time_data_exchange.set_input_data(input_dict)

    def __move_at_speed_callback(self,data):
        linear = data.linear
        angular = data.angular


        self.movement_counter += 1

        input_dict = {
        Driver.Registers.X: linear.x,
        Driver.Registers.Y: linear.y,
        Driver.Registers.Z: linear.z,
        Driver.Registers.RX: angular.x,
        Driver.Registers.RY: angular.y,
        Driver.Registers.RZ: angular.z,
        Driver.Registers.MOVEMENT_TYPE   : 3, #movment type
        Driver.Registers.MOVEMENT_COUNTER_INPUT   : self.movement_counter
        }

        self.real_time_data_exchange.set_input_data(input_dict)

    def __gripper_pos_callback(self,data):

        self.gripper_counter += 1
        input_dict = {
        Driver.Registers.GRIPPER_POS_INPUT: data.data,
        Driver.Registers.GRIPPER_SPEED_INPUT: 100.0,
        Driver.Registers.GRIPPER_FORCE_INPUT: 100.0,
        Driver.Registers.GRIPPER_COUNTER_INPUT   : self.gripper_counter
        }

        self.real_time_data_exchange.set_input_data(input_dict)


if __name__ == "__main__":
    with Driver("10.90.184.11") as driver:
        print("ur driver starting spin")
        rospy.spin()
