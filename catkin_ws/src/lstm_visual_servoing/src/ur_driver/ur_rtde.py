#!/usr/bin/env python

#https://www.universal-robots.com/how-tos-and-faqs/how-to/ur-how-tos/real-time-data-exchange-rtde-guide-22229/
from os import wait
import socket # https://docs.python.org/3/library/socket.html
import time
import threading #https://docs.python.org/3/library/threading.html
import struct # https://docs.python.org/3/library/struct.html


class UrRealTimeDataExchange():
    """
    This class will connect the the UR Controller over ethernet and
    try to continuously sync all the Real Time Data Exchange input and
    output variables with python dictionaries.

    This class will start multiple threads for reading and writing to the
    UR Controller and for useage as watchdog. If there are any issues with
    the connection or the UR Controller restarts this class should reconnect
    by its self.

    ### INTENDED USAGE ###
    with UrRealTimeSync("XXX.XXX.XXX.XXX") as rt:
        rt.set_intput_data({"input_int_register_0":1234})

        output_dict = {"actual_TCP_pose": None}
        rt.get_output_data(output_dict)
        x,y,z,rx,ry,rz = output_dict["actual_TCP_pose"]

    The UR Controller provides this Real Time Data Exchange (RTDE) interface
    that can be accessed over ethernet on port 30004. The UR Controller
    has a list of input and output variables that can be written to and
    read from. When this class first connects to the UR Controller it will send some
    strings listing the variables it wants to read and write too. From then
    on the data for these variables will be sent back and forwards in
    a binary format.
    """


    def __init__(self,robot_ip_address):
        """
        Constructor - initialises instance variables
        """

        #take instance copy of ip addreess
        self.robot_ip_address = robot_ip_address
        self.real_time_socket = None
        self.alive = True
        self.watchdog_healthy = True

        #create the threading objects with correct methods to thread
        self.send_loop_thread = threading.Thread(target=self.__send_loop, name="Send Thread")
        self.recv_loop_thread = threading.Thread(target=self.__recv_loop, name="Receive Thread")
        self.watchdog_loop_thread = threading.Thread(target=self.__watchdog_loop, name="Watchdog Thread")

        #create some lock objects to prevent clashes when setting and getting
        #data from the dicts
        self.input_lock = threading.Lock()
        self.output_lock = threading.Lock()

        #initalise strings to hold input and output recipies.
        #recipies are comma seperated variable names
        #eg "timestamp,target_q"
        self.input_recipe_string = ""
        self.output_recipe_string = ""

        #initialise format string. Format strings are a list of Characters that
        #specify how data should be packed and unpaked into a binary format for
        #sending over ethernet
        # ! = specify all data is in network byte order
        # B = unsigned char
        # l = long
        # etc.. see https://docs.python.org/3/library/struct.html
        self.input_data_format = "!B"
        self.output_data_format = "!"

        #main data dictionaries used for holding of the data that is synced
        #with the UR Controller
        self.input_rtde_dict = {}
        self.output_rtde_dict = {}

        # Iterate over the input recipe description and create the format string, the recipe string, and the dictionary
        for  variable_name, data_type, array_length, format_char, default_value, description in UrRealTimeDataExchange.rtde_input_recipe_description:
            #append the format character. Some variable are arrays so repeat the format char by the array length
            self.input_data_format += format_char * array_length
            #append variable names to the recipe string with a comma
            self.input_recipe_string +=  variable_name + ","
            #populate the dictionary with variable names and default values
            self.input_rtde_dict[variable_name] = default_value
        #remove the last comma
        self.input_recipe_string = self.input_recipe_string[:-1]

        # Iterate over the input recipe description and create the format string, the recipe string, and the dictionary
        for  variable_name, data_type, array_length, format_char, default_value, description in UrRealTimeDataExchange.rtde_output_recipe_description:
            #append the format character. Some variable are arrays so repeat the format char by the array length
            self.output_data_format += format_char * array_length
            #append variable names to the recipe string with a comma
            self.output_recipe_string +=  variable_name + ","
            #populate the dictionary with variable names and default values
            self.output_rtde_dict[variable_name] = default_value
        #remove the last comma
        self.output_recipe_string = self.output_recipe_string[:-1]

        #Create a dictionary to hold system information
        self.robot_system_state_dict = {}
        self.robot_system_state_dict["controller_version_minor"] = 0
        self.robot_system_state_dict["controller_version_major"] = 0
        self.robot_system_state_dict["controller_version_build"] = 0
        self.robot_system_state_dict["controller_version_bugfix"] = 0
        self.robot_system_state_dict["start_accepted"] = 0
        self.robot_system_state_dict["stop_accepted"] = 0
        self.robot_system_state_dict["input_recipe_id"] = 0

    def __enter__(self):
        """
        Starts all threads. Should be called from with context manager
        """
        self.send_loop_thread.start()
        self.recv_loop_thread.start()
        self.watchdog_loop_thread.start()
        return self

    def __exit__(self,*args):
        """
        Stops all threads. Should be called from with context manager
        """
        self.alive = False
        self.send_loop_thread.join()
        self.recv_loop_thread.join()
        self.watchdog_loop_thread.join()
        # print("\nJoined")

    def __send_loop(self):
        """
        The send loop should be run in a seperate thread.
        The body of this method is a while try structure which means
        it tries its best to stay connect to robot and sending messages. If
        there are any exceptions they are cought and while loop tries all over
        again
        """
        #wrap everything in a while try structure so that it tries its best
        #to stay connected with the robot. If everything works correctly then
        #this outer while loop should only run once
        while self.alive:
            time.sleep(0.1) #Retry at ~10 hz
            try:
                #set the robot system info to default values
                self.robot_system_state_dict["controller_version_minor"] = 0
                self.robot_system_state_dict["controller_version_major"] = 0
                self.robot_system_state_dict["controller_version_build"] = 0
                self.robot_system_state_dict["controller_version_bugfix"] = 0
                self.robot_system_state_dict["start_accepted"] = 0
                self.robot_system_state_dict["stop_accepted"] = 0
                self.robot_system_state_dict["input_recipe_id"] = 0

                # create a socket object and set a few socket options
                self.real_time_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Ethernet TCP
                #self.real_time_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #not sure if this is needed by just copied this
                #self.real_time_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) #not sure if this is needed by just copied this
                self.real_time_socket.settimeout(1) #timeout of 1 second
                self.real_time_socket.connect((self.robot_ip_address, 30004)) # port 30004 is the real time data exchange interface

                #send some setup packages to the robot.
                #Resposes are handled by the recv loop below
                self.__sendPackage(UrRealTimeDataExchange.Command.RTDE_GET_URCONTROL_VERSION) #ask it for its version
                self.__sendPackage(UrRealTimeDataExchange.Command.RTDE_CONTROL_PACKAGE_SETUP_INPUTS,self.input_recipe_string) #tell it the input variables we want to use
                self.__sendPackage(UrRealTimeDataExchange.Command.RTDE_CONTROL_PACKAGE_SETUP_OUTPUTS,self.output_recipe_string) #tell it the output variables we want to use
                self.__sendPackage(UrRealTimeDataExchange.Command.RTDE_CONTROL_PACKAGE_START) #send the start command.

                #Assume all is good and set the watchdog healthy
                self.watchdog_healthy = True

                #while alive and healthy keep sending input data to the robot
                while self.alive and self.watchdog_healthy:
                    time.sleep(0.01) #send at ~100Hz
                    #thread lock the input data to make sure no one edits the
                    #dictionary while we are trying to read it
                    with self.input_lock:
                        #use the data format and dict to list generator to
                        #serialise all the input varaibles ready for sending to the robot
                        input_payload = struct.pack(self.input_data_format,*self.__input_data_dict_list_generator())
                    #send the data to the robot with data package command
                    self.__sendPackage(UrRealTimeDataExchange.Command.RTDE_DATA_PACKAGE,input_payload)


            #If there is an socket based error, supress it and let the outer
            #while loop try again
            except (OSError,socket.timeout,socket.error) as e:
                #print("send error %s" % e)
                pass

            #If there is any other exception we were not expecting, set alive
            #to false to stop the other threads then re raise the Exception
            #so that the user can know about it
            except Exception:
                self.alive = False
                raise

            finally:
                #Close the socket and sleep a little so we don't use all the CPU
                #trying to reconnect
                self.real_time_socket.close()


    def __recv_loop(self):
        #each message sent to and from the robot has the following format
        #[length   , command  , payload]
        #[2 x bytes, 1 x bytes, (lenght-3) x bytes]

        #create a dict of all the possible command callbacks
        command_callback_dict = {}
        command_callback_dict[UrRealTimeDataExchange.Command.RTDE_REQUEST_PROTOCOL_VERSION]         = self.__requestProtocolVersionCallback
        command_callback_dict[UrRealTimeDataExchange.Command.RTDE_GET_URCONTROL_VERSION]            = self.__getUrControlVersionCallback
        command_callback_dict[UrRealTimeDataExchange.Command.RTDE_TEXT_MESSAGE]                     = self.__textMessageCallback
        command_callback_dict[UrRealTimeDataExchange.Command.RTDE_DATA_PACKAGE]                     = self.__dataPackageCallback
        command_callback_dict[UrRealTimeDataExchange.Command.RTDE_CONTROL_PACKAGE_SETUP_OUTPUTS]    = self.__controlPackageSetupOutputsCallback
        command_callback_dict[UrRealTimeDataExchange.Command.RTDE_CONTROL_PACKAGE_SETUP_INPUTS]     = self.__controlPackageSetupInputsCallback
        command_callback_dict[UrRealTimeDataExchange.Command.RTDE_CONTROL_PACKAGE_START]            = self.__controlPackageStartCallback
        command_callback_dict[UrRealTimeDataExchange.Command.RTDE_CONTROL_PACKAGE_PAUSE]            = self.__controlPackagePauseCallback

        #create buffer to receive into
        recv_buffer = b""

        #While try to ensure we keep trying to read regardless of the socket
        #based exception that arise
        while self.alive:
            try:
                #Check that the socket objects exists
                if self.real_time_socket != None:
                    #append any new bytes to the buffer
                    recv_buffer += self.real_time_socket.recv(4096)

                    #if there are at least 3 bytes then we can read the package header
                    if len(recv_buffer) >= 3:
                        #slice out the header bytes
                        header = recv_buffer[:3]
                        #unpack the bytes into
                        pkg_size,pkg_cmd = struct.unpack("!HB",header)

                        #if we have received all the bytes in the package
                        if len(recv_buffer) >= pkg_size:
                            #cut out the payload from the buffer
                            payload = recv_buffer[3:pkg_size]
                            #remove this whole package from the buffer
                            recv_buffer = recv_buffer[pkg_size:]

                            #if the package command is in the dict of callbacks
                            if pkg_cmd in command_callback_dict:
                                #pass the payload to the correct callback
                                command_callback_dict[pkg_cmd](payload)

            #Supress any socket based exception and keep trying to receive
            except (OSError,socket.timeout,socket.error) as e:
                time.sleep(0.1) #Retry at ~10 hz
                #print("recv error %s" % e)

            #Catch an other exception and set alive false to stop the other threads
            except Exception:
                self.alive = False
                #Re raise the exception to let the user know
                raise

    def __watchdog_loop(self):
        """
        This watchdog loop just runs in the background checking if a series of
        conditions are healty. If the conditions are unhealthy for a certain
        amount of time the the watchdog_healthy flag becomes false
        """
        timeout_time = 1.0 #seconds

        last_timestamp = 0.0
        last_time = time.time()
        while self.alive:
            time.sleep(0.1) #~10hz

            #concatenate healthy conditions with and equals operator
            healthy = self.robot_system_state_dict["start_accepted"] == True #UR Controller accepted output recipe
            healthy &= self.robot_system_state_dict["input_recipe_id"] != 0 #UR Controler accepted input recipe and gave us a recipe id
            healthy &= not last_timestamp == self.output_rtde_dict["timestamp"] #time stamp has changed meaning its receiving data

            #update the last time stamp
            last_timestamp = self.output_rtde_dict["timestamp"]

            #if all conditions are health then reset the timer
            if healthy:
                last_time = time.time()

            #if the watchdog is curretly healthy check if it should still be
            if self.watchdog_healthy:
                #check if the timout time has elapsed
                if time.time() - last_time > timeout_time:
                    #watch dog not health
                    self.watchdog_healthy = False
                    #reset the timer
                    last_time = time.time()
                    # print("\n\nWatchdog ######################################################################################\n")
                    # print(self.robot_system_state_dict["start_accepted"])
                    # print(self.robot_system_state_dict["input_recipe_id"])
                    # print(self.output_rtde_dict["timestamp"])
            else:
                #if watchdog_healthy is false then reset the timer
                last_time = time.time()



    def __input_data_dict_list_generator(self):
        """
        This generator will use the __rtde_input_recipe_description to turn the input_data_dict
        into the appearnce of an list. This is primarialy used by struct.pack
        to create a byte array to send over the ethernet
        """
        yield self.robot_system_state_dict["input_recipe_id"]
        for  variable_name, data_type, array_length, format_char, default_value, description in UrRealTimeDataExchange.rtde_input_recipe_description:
            if array_length > 1:
                for value in self.input_rtde_dict[ variable_name]:
                    yield value
            else:
                yield self.input_rtde_dict[ variable_name]

    def __sendPackage(self,command,payload=""):
        #create the package header from leghth and command
        header = struct.pack("!HB",len(payload)+3,command)

        if isinstance(payload,str):
            payload = payload.encode()

        #append the payload to the header to create the whole package
        package = header + payload

        #send all bytes out the socket to the robot
        self.real_time_socket.sendall(package)

    def set_input_data(self,input_dict):
        """
        Asyncronously set input data to send to the robot.

        USAGE
        with UrRealTimeSync("XXX.XXX.XXX.XXX") as rt:
            rt.set_intput_data({"input_int_register_0":1234})

        This method is thread safe so you can garentee that all the data
        is copied into the input dict before it's sent to the robot
        """
        with self.input_lock:
            for key,val in input_dict.items():
                self.input_rtde_dict[key] = val

    def get_output_data(self,output_dict):
        """
        Asyncronously get output data received from the robot.

        USAGE
        with UrRealTimeSync("XXX.XXX.XXX.XXX") as rt:
            output_data = {"output_int_register_0":None}
            rt.get_outtput_data(output_data)
            print(output_data["output_int_register_0"])

        This method is thread safe so you can garentee that all the data
        is receivied before you get a copy
        """
        with self.output_lock:
            for key in output_dict.keys():
                output_dict[key] = self.output_rtde_dict[key]

    def __requestProtocolVersionCallback(self,payload):
        self.robot_system_state_dict["protocol_version"], = struct.unpack("!H",payload)

    def __getUrControlVersionCallback(self,payload):
        major, minor, bugfix, build = struct.unpack("!IIII",payload)
        self.robot_system_state_dict["controller_version_major"] = major
        self.robot_system_state_dict["controller_version_minor"] = minor
        self.robot_system_state_dict["controller_version_bugfix"] = bugfix
        self.robot_system_state_dict["controller_version_build"] = build

    def __textMessageCallback(self,payload):
        message_type, = struct.unpack("!B",payload[:1])
        message = payload[1:]
        # print("Text Message: %i, %s" % (message_type,message))

    def __dataPackageCallback(self,payload):
        values = struct.unpack(self.output_data_format,payload)

        with self.input_lock:
            i = 0
            for  variable_name, data_type, array_length, format_char, default_value, description in UrRealTimeDataExchange.rtde_output_recipe_description:
                if array_length > 1:
                    array = self.output_rtde_dict[ variable_name]
                    for j in range(array_length):
                        array[j] = values[i]
                        i += 1
                else:
                    self.output_rtde_dict[ variable_name] = values[i]
                    i += 1

    def __controlPackageSetupInputsCallback(self,payload):
        print(payload[:1])
        self.robot_system_state_dict["input_recipe_id"], = struct.unpack("!B",payload[:1])
        # print("\nInput Setup")
        # typeStrs = payload[1:].split(",")
        #TODO check that retured data types matches what we asked for
        # if self.robot_system_state_dict["input_recipe_id"] != 1:
        #     for i in range(len(typeStrs)):
        #         print("%33s: %16s %16s %s" % (input_description[i][0],input_description[i][1],typeStrs[i],input_description[i][3]))

    def __controlPackageSetupOutputsCallback(self,payload):
        # print("\nOutput Setup")
        payload = payload.decode()
        typeStrs = payload.split(",")
        #TODO check that retured data types matches what we asked for
        # for i in range(len(typeStrs)):
        #     print("%33s: %16s %16s %s" % (output_description[i][0],output_description[i][1],typeStrs[i],output_description[i][3]))

    def __controlPackageStartCallback(self,payload):
        self.robot_system_state_dict["start_accepted"], = struct.unpack("!?",payload)

    def __controlPackagePauseCallback(self,payload):
        self.robot_system_state_dict["stop_accepted"], = struct.unpack("!?",payload)




    class Command:
        RTDE_REQUEST_PROTOCOL_VERSION = 86        # ascii V
        RTDE_GET_URCONTROL_VERSION = 118          # ascii v
        RTDE_TEXT_MESSAGE = 77                    # ascii M
        RTDE_DATA_PACKAGE = 85                    # ascii U
        RTDE_CONTROL_PACKAGE_SETUP_OUTPUTS = 79   # ascii O
        RTDE_CONTROL_PACKAGE_SETUP_INPUTS = 73    # ascii I
        RTDE_CONTROL_PACKAGE_START = 83           # ascii S
        RTDE_CONTROL_PACKAGE_PAUSE = 80           # ascii P

    #(Variable Name, Data Type, Array Lenght, Struct Format Character, Default Value, Description)
    rtde_input_recipe_description = [
        ("speed_slider_mask","UINT32",1,"I",0,"0 = don't change speed slider with this input, 1 = use speed_slider_fraction to set speed slider value"),
        ("speed_slider_fraction","DOUBLE",1,"d",0,"new speed slider value"),
        ("standard_digital_output_mask","UINT8",1,"B",0,"Standard digital output bit mask*"),
        ("standard_digital_output","UINT8",1,"B",0,"Standard digital outputs"),
        ("configurable_digital_output_mask","UINT8",1,"B",0,"Configurable digital output bit mask*"),
        ("configurable_digital_output","UINT8",1,"B",0,"Configurable digital outputs"),
        ("tool_digital_output_mask","UINT8",1,"B",0,"Tool digital outputs mask*, Bits 0-1: mask, remaining bits are reserved for future use"),
        ("tool_digital_output","UINT8",1,"B",0,"Tool digital outputs, Bits 0-1: output state, remaining bits are reserved for future use"),
        ("standard_analog_output_mask","UINT8",1,"B",0,"Standard analog output mask, Bits 0-1: standard_analog_output_0 | standard_analog_output_1"),
        ("standard_analog_output_type","UINT8",1,"B",0,"Output domain {0=current[A], 1=voltage[V]}, Bits 0-1: standard_analog_output_0 | standard_analog_output_1"),
        ("standard_analog_output_0","DOUBLE",1,"d",0,"Standard analog output 0 (ratio) [0..1]"),
        ("standard_analog_output_1","DOUBLE",1,"d",0,"Standard analog output 1 (ratio) [0..1]"),
        ("input_bit_registers0_to_31","UINT32",1,"I",0,"General purpose input bits"),
        ("input_bit_registers32_to_63","UINT32",1,"I",0,"General purpose input bits"),
        ("input_int_register_0","INT32",1,"i",0,"General purpose input integer register 0"),
        ("input_int_register_1","INT32",1,"i",0,"General purpose input integer register 1"),
        ("input_int_register_2","INT32",1,"i",0,"General purpose input integer register 2"),
        ("input_int_register_3","INT32",1,"i",0,"General purpose input integer register 3"),
        ("input_int_register_4","INT32",1,"i",0,"General purpose input integer register 4"),
        ("input_int_register_5","INT32",1,"i",0,"General purpose input integer register 5"),
        ("input_int_register_6","INT32",1,"i",0,"General purpose input integer register 6"),
        ("input_int_register_7","INT32",1,"i",0,"General purpose input integer register 7"),
        ("input_int_register_8","INT32",1,"i",0,"General purpose input integer register 8"),
        ("input_int_register_9","INT32",1,"i",0,"General purpose input integer register 9"),
        ("input_int_register_10","INT32",1,"i",0,"General purpose input integer register 10"),
        ("input_int_register_11","INT32",1,"i",0,"General purpose input integer register 11"),
        ("input_int_register_12","INT32",1,"i",0,"General purpose input integer register 12"),
        ("input_int_register_13","INT32",1,"i",0,"General purpose input integer register 13"),
        ("input_int_register_14","INT32",1,"i",0,"General purpose input integer register 14"),
        ("input_int_register_15","INT32",1,"i",0,"General purpose input integer register 15"),
        ("input_int_register_16","INT32",1,"i",0,"General purpose input integer register 16"),
        ("input_int_register_17","INT32",1,"i",0,"General purpose input integer register 17"),
        ("input_int_register_18","INT32",1,"i",0,"General purpose input integer register 18"),
        ("input_int_register_19","INT32",1,"i",0,"General purpose input integer register 19"),
        ("input_int_register_20","INT32",1,"i",0,"General purpose input integer register 20"),
        ("input_int_register_21","INT32",1,"i",0,"General purpose input integer register 21"),
        ("input_int_register_22","INT32",1,"i",0,"General purpose input integer register 22"),
        ("input_int_register_23","INT32",1,"i",0,"General purpose input integer register 23"),
        ("input_double_register_0","DOUBLE",1,"d",0,"General purpose input double register 0"),
        ("input_double_register_1","DOUBLE",1,"d",0,"General purpose input double register 1"),
        ("input_double_register_2","DOUBLE",1,"d",0,"General purpose input double register 2"),
        ("input_double_register_3","DOUBLE",1,"d",0,"General purpose input double register 3"),
        ("input_double_register_4","DOUBLE",1,"d",0,"General purpose input double register 4"),
        ("input_double_register_5","DOUBLE",1,"d",0,"General purpose input double register 5"),
        ("input_double_register_6","DOUBLE",1,"d",0,"General purpose input double register 6"),
        ("input_double_register_7","DOUBLE",1,"d",0,"General purpose input double register 7"),
        ("input_double_register_8","DOUBLE",1,"d",0,"General purpose input double register 8"),
        ("input_double_register_9","DOUBLE",1,"d",0,"General purpose input double register 9"),
        ("input_double_register_10","DOUBLE",1,"d",0,"General purpose input double register 10"),
        ("input_double_register_11","DOUBLE",1,"d",0,"General purpose input double register 11"),
        ("input_double_register_12","DOUBLE",1,"d",0,"General purpose input double register 12"),
        ("input_double_register_13","DOUBLE",1,"d",0,"General purpose input double register 13"),
        ("input_double_register_14","DOUBLE",1,"d",0,"General purpose input double register 14"),
        ("input_double_register_15","DOUBLE",1,"d",0,"General purpose input double register 15"),
        ("input_double_register_16","DOUBLE",1,"d",0,"General purpose input double register 16"),
        ("input_double_register_17","DOUBLE",1,"d",0,"General purpose input double register 17"),
        ("input_double_register_18","DOUBLE",1,"d",0,"General purpose input double register 18"),
        ("input_double_register_19","DOUBLE",1,"d",0,"General purpose input double register 19"),
        ("input_double_register_20","DOUBLE",1,"d",0,"General purpose input double register 20"),
        ("input_double_register_21","DOUBLE",1,"d",0,"General purpose input double register 21"),
        ("input_double_register_22","DOUBLE",1,"d",0,"General purpose input double register 22"),
        ("input_double_register_23","DOUBLE",1,"d",0,"General purpose input double register 23")
    ]

    #(Variable Name, Data Type, Array Lenght, Struct Format Character, Default Value, Description)
    rtde_output_recipe_description = [
        ("timestamp","DOUBLE",1,"d",0,"Time elapsed since the controller was started [s]"),
        ("target_q","VECTOR6D",6,"d",[0.0,0.0,0.0,0.0,0.0,0.0],"Target joint positions"),
        ("target_qd","VECTOR6D",6,"d",[0.0,0.0,0.0,0.0,0.0,0.0],"Target joint velocities"),
        ("target_qdd","VECTOR6D",6,"d",[0.0,0.0,0.0,0.0,0.0,0.0],"Target joint accelerations"),
        ("target_current","VECTOR6D",6,"d",[0.0,0.0,0.0,0.0,0.0,0.0],"Target joint currents"),
        ("target_moment","VECTOR6D",6,"d",[0.0,0.0,0.0,0.0,0.0,0.0],"Target joint moments (torques)"),
        ("actual_q","VECTOR6D",6,"d",[0.0,0.0,0.0,0.0,0.0,0.0],"Actual joint positions"),
        ("actual_qd","VECTOR6D",6,"d",[0.0,0.0,0.0,0.0,0.0,0.0],"Actual joint velocities"),
        ("actual_current","VECTOR6D",6,"d",[0.0,0.0,0.0,0.0,0.0,0.0],"Actual joint currents"),
        ("joint_control_output","VECTOR6D",6,"d",[0.0,0.0,0.0,0.0,0.0,0.0],"Joint control currents"),
        ("actual_TCP_pose","VECTOR6D",6,"d",[0.0,0.0,0.0,0.0,0.0,0.0],"Actual Cartesian coordinates of the tool: (x,y,z,rx,ry,rz), where rx, ry and rz is a rotation vector representation of the tool orientation"),
        ("actual_TCP_speed","VECTOR6D",6,"d",[0.0,0.0,0.0,0.0,0.0,0.0],"Actual speed of the tool given in Cartesian coordinates"),
        ("actual_TCP_force","VECTOR6D",6,"d",[0.0,0.0,0.0,0.0,0.0,0.0],"Generalized forces in the TCP"),
        ("target_TCP_pose","VECTOR6D",6,"d",[0.0,0.0,0.0,0.0,0.0,0.0],"Target Cartesian coordinates of the tool: (x,y,z,rx,ry,rz), where rx, ry and rz is a rotation vector representation of the tool orientation"),
        ("target_TCP_speed","VECTOR6D",6,"d",[0.0,0.0,0.0,0.0,0.0,0.0],"Target speed of the tool given in Cartesian coordinates"),
        ("actual_digital_input_bits","UINT64",1,"Q",0,"Current state of the digital inputs. 0-7: Standard, 8-15: Configurable, 16-17: Tool"),
        ("joint_temperatures","VECTOR6D",6,"d",[0.0,0.0,0.0,0.0,0.0,0.0],"Temperature of each joint in degrees Celsius"),
        ("actual_execution_time","DOUBLE",1,"d",0,"Controller real-time thread execution time"),
        ("robot_mode","INT32",1,"i",0,"Robot mode"),
        ("joint_mode","VECTOR6INT32",6,"i",[0,0,0,0,0,0],"Joint control modes"),
        ("safety_mode","INT32",1,"i",0,"Safety mode"),
        ("actual_tool_accelerometer","VECTOR3D",3,"d",[0.0,0.0,0.0],"Tool x, y and z accelerometer values"),
        ("speed_scaling","DOUBLE",1,"d",0,"Speed scaling of the trajectory limiter"),
        ("target_speed_fraction","DOUBLE",1,"d",0,"Target speed fraction"),
        ("actual_momentum","DOUBLE",1,"d",0,"Norm of Cartesian linear momentum"),
        ("actual_main_voltage","DOUBLE",1,"d",0,"Safety Control Board: Main voltage"),
        ("actual_robot_voltage","DOUBLE",1,"d",0,"Safety Control Board: Robot voltage (48V)"),
        ("actual_robot_current","DOUBLE",1,"d",0,"Safety Control Board: Robot current"),
        ("actual_joint_voltage","VECTOR6D",6,"d",[0.0,0.0,0.0,0.0,0.0,0.0],"Actual joint voltages"),
        ("actual_digital_output_bits","UINT64",1,"Q",0,"Current state of the digital outputs. 0-7: Standard, 8-15: Configurable, 16-17: Tool"),
        ("runtime_state","UINT32",1,"I",0,"Program state"),
        #("elbow_position","VECTOR3D",3,"d",[0.0,0.0,0.0],"Actual cartesian coordinates of the elbow (x,y,z)"),
        #("elbow_velocity","VECTOR3D",3,"d",[0.0,0.0,0.0],"Actual cartesian velocity of the elbow"),
        ("robot_status_bits","UINT32",1,"I",0,"Bits 0-3: Is power on | Is program running | Is teach button pressed | Is power button pressed"),
        ("safety_status_bits","UINT32",1,"I",0,"Bits 0-10: Is normal mode | Is reduced mode | | Is protective stopped | Is recovery mode | Is safeguard stopped | Is system emergency stopped | Is robot emergency stopped | Is emergency stopped | Is violation | Is fault | Is stopped due to safety"),
        ("analog_io_types","UINT32",1,"I",0,"Bits 0-3: analog input 0 | analog input 1 | analog output 0 | analog output 1, {0=current[A], 1=voltage[V]}"),
        ("standard_analog_input0","DOUBLE",1,"d",0,"Standard analog input 0 [A or V]"),
        ("standard_analog_input1","DOUBLE",1,"d",0,"Standard analog input 1 [A or V]"),
        ("standard_analog_output0","DOUBLE",1,"d",0,"Standard analog output 0 [A or V]"),
        ("standard_analog_output1","DOUBLE",1,"d",0,"Standard analog output 1 [A or V]"),
        ("io_current","DOUBLE",1,"d",0,"I/O current [A]"),
        ("euromap67_input_bits","UINT32",1,"I",0,"Euromap67 input bits"),
        ("euromap67_output_bits","UINT32",1,"I",0,"Euromap67 output bits"),
        ("euromap67_24V_voltage","DOUBLE",1,"d",0,"Euromap 24V voltage [V]"),
        ("euromap67_24V_current","DOUBLE",1,"d",0,"Euromap 24V current [A]"),
        ("tool_mode","UINT32",1,"I",0,"Tool mode"),
        ("tool_analog_input_types","UINT32",1,"I",0,"Output domain {0=current[A], 1=voltage[V]}, Bits 0-1: tool_analog_input_0 | tool_analog_input_1"),
        ("tool_analog_input0","DOUBLE",1,"d",0,"Tool analog input 0 [A or V]"),
        ("tool_analog_input1","DOUBLE",1,"d",0,"Tool analog input 1 [A or V]"),
        # ("tool_output_voltage","INT32",1,"i",0,"Tool output voltage [V]"), # for some reason the robot doesn't return bytes for this value despite the output setup working correctly
        ("tool_output_current","DOUBLE",1,"d",0,"Tool current [A]"),
        #("tool_temperature","DOUBLE",1,"d",0,"Tool temperature in degrees Celsius"),
        ("tcp_force_scalar","DOUBLE",1,"d",0,"TCP force scalar [N]"),
        ("output_bit_registers0_to_31","UINT32",1,"I",0,"General purpose output bits"),
        ("output_bit_registers32_to_63","UINT32",1,"I",0,"General purpose output bits"),
        ("output_int_register_0","INT32",1,"i",0,"General purpose output integer register 0"),
        ("output_int_register_1","INT32",1,"i",0,"General purpose output integer register 1"),
        ("output_int_register_2","INT32",1,"i",0,"General purpose output integer register 2"),
        ("output_int_register_3","INT32",1,"i",0,"General purpose output integer register 3"),
        ("output_int_register_4","INT32",1,"i",0,"General purpose output integer register 4"),
        ("output_int_register_5","INT32",1,"i",0,"General purpose output integer register 5"),
        ("output_int_register_6","INT32",1,"i",0,"General purpose output integer register 6"),
        ("output_int_register_7","INT32",1,"i",0,"General purpose output integer register 7"),
        ("output_int_register_8","INT32",1,"i",0,"General purpose output integer register 8"),
        ("output_int_register_9","INT32",1,"i",0,"General purpose output integer register 9"),
        ("output_int_register_10","INT32",1,"i",0,"General purpose output integer register 10"),
        ("output_int_register_11","INT32",1,"i",0,"General purpose output integer register 11"),
        ("output_int_register_12","INT32",1,"i",0,"General purpose output integer register 12"),
        ("output_int_register_13","INT32",1,"i",0,"General purpose output integer register 13"),
        ("output_int_register_14","INT32",1,"i",0,"General purpose output integer register 14"),
        ("output_int_register_15","INT32",1,"i",0,"General purpose output integer register 15"),
        ("output_int_register_16","INT32",1,"i",0,"General purpose output integer register 16"),
        ("output_int_register_17","INT32",1,"i",0,"General purpose output integer register 17"),
        ("output_int_register_18","INT32",1,"i",0,"General purpose output integer register 18"),
        ("output_int_register_19","INT32",1,"i",0,"General purpose output integer register 19"),
        ("output_int_register_20","INT32",1,"i",0,"General purpose output integer register 20"),
        ("output_int_register_21","INT32",1,"i",0,"General purpose output integer register 21"),
        # ("output_int_register_22","INT32",1,"i",0,"General purpose output integer register 22"), # for some reason the robot can't handle a recipe string larger than 2048 bytes so i just removed some registeres
        # ("output_int_register_23","INT32",1,"i",0,"General purpose output integer register 23"), # for some reason the robot can't handle a recipe string larger than 2048 bytes so i just removed some registeres
        ("output_double_register_0","DOUBLE",1,"d",0,"General purpose output double register 0"),
        ("output_double_register_1","DOUBLE",1,"d",0,"General purpose output double register 1"),
        ("output_double_register_2","DOUBLE",1,"d",0,"General purpose output double register 2"),
        ("output_double_register_3","DOUBLE",1,"d",0,"General purpose output double register 3"),
        ("output_double_register_4","DOUBLE",1,"d",0,"General purpose output double register 4"),
        ("output_double_register_5","DOUBLE",1,"d",0,"General purpose output double register 5"),
        ("output_double_register_6","DOUBLE",1,"d",0,"General purpose output double register 6"),
        ("output_double_register_7","DOUBLE",1,"d",0,"General purpose output double register 7"),
        ("output_double_register_8","DOUBLE",1,"d",0,"General purpose output double register 8"),
        ("output_double_register_9","DOUBLE",1,"d",0,"General purpose output double register 9"),
        ("output_double_register_10","DOUBLE",1,"d",0,"General purpose output double register 10"),
        ("output_double_register_11","DOUBLE",1,"d",0,"General purpose output double register 11"),
        ("output_double_register_12","DOUBLE",1,"d",0,"General purpose output double register 12"),
        ("output_double_register_13","DOUBLE",1,"d",0,"General purpose output double register 13"),
        ("output_double_register_14","DOUBLE",1,"d",0,"General purpose output double register 14"),
        ("output_double_register_15","DOUBLE",1,"d",0,"General purpose output double register 15"),
        ("output_double_register_16","DOUBLE",1,"d",0,"General purpose output double register 16"),
        ("output_double_register_17","DOUBLE",1,"d",0,"General purpose output double register 17"),
        ("output_double_register_18","DOUBLE",1,"d",0,"General purpose output double register 18"),
        ("output_double_register_19","DOUBLE",1,"d",0,"General purpose output double register 19"),
        ("output_double_register_20","DOUBLE",1,"d",0,"General purpose output double register 20"),
        ("output_double_register_21","DOUBLE",1,"d",0,"General purpose output double register 21")
        # ("output_double_register_22","DOUBLE",1,"d",0,"General purpose output double register 22"), # for some reason the robot can't handle a recipe string larger than 2048 bytes so i just removed some registeres
        # ("output_double_register_23","DOUBLE",1,"d",0,"General purpose output double register 23") # for some reason the robot can't handle a recipe string larger than 2048 bytes so i just removed some registeres
    ]

def test():
    with UrRealTimeDataExchange("129.127.10.110") as rt:
        try:
            time.sleep(1)
            while rt.alive:
                rt.set_input_data({"input_int_register_0":2})

                out = {"timestamp":None,"actual_TCP_pose":None}
                rt.get_output_data(out)


                print(rt.robot_system_state_dict)

                print("\n\nOutput Data:")
                for  variable_name, data_type, array_length, format_char, default_value, description in UrRealTimeDataExchange.rtde_output_recipe_description:
                    print("%30s: %s" % ( variable_name,str(rt.output_rtde_dict[ variable_name])))

                print(out)
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    test()
