#!/usr/bin/env python3
import rospy
import std_msgs.msg
import sensor_msgs.msg
import geometry_msgs.msg
import lstm_visual_servoing.msg

class UserInput:
    def __init__(self):
        rospy.init_node('user_input', anonymous=False)
        rospy.Subscriber("joy", sensor_msgs.msg.Joy, self.joystick_callback)

        self.ctrl_pub = rospy.Publisher("visual_control",lstm_visual_servoing.msg.Control,queue_size=10)
        self.record_pub = rospy.Publisher("record_enabled",lstm_visual_servoing.msg.Recorder,queue_size=10)

        self._claw_state = "open"

    def spin(self):
        print("User Input Spinning")
        # Create blank message
        self.ctrl_msg = lstm_visual_servoing.msg.Control()
        self.record_msg = lstm_visual_servoing.msg.Recorder()

        # Publish the latest control message at 30Hz
        r = rospy.Rate(20)
        while not rospy.is_shutdown():
            self.ctrl_pub.publish(self.ctrl_msg)
            self.record_pub.publish(self.record_msg)
            r.sleep()

    def joystick_callback(self,data):
        # Get all the axes and button values
        left_x, left_y, trig_l, right_x, right_y, trig_r, dpad_x, dpad_y = data.axes
        btn_a, btn_b, btn_x, btn_y, bump_l, bump_r, back, menu, _, stick_l, stick_r = data.buttons

        # Create a new robot control message
        msg = lstm_visual_servoing.msg.Control()

        # Translation
        msg.vx = - deadband(left_x)
        msg.vy = - deadband(left_y)
        msg.vz = deadband(trig_l/2.0 - trig_r/2.0)

        # Rotation
        msg.rx =  deadband(right_y)
        msg.ry = - deadband(right_x)
        msg.rz = bump_r - bump_l

        # Claw 0.0 = open, 1.0 = closed, default open
        msg.claw = 0.0 if self._claw_state == "open" else 1.0
        if btn_a == 0.0 and btn_b == 1.0 and self._claw_state == "open":
            self._claw_state = "closed"
            msg.claw = 1.0
        if btn_a == 1.0 and btn_b == 0.0 and self._claw_state == "closed":
            self._claw_state = "open"
            msg.claw = 0.0

        self.ctrl_msg = msg

        # Create a new Recorder message
        msg = lstm_visual_servoing.msg.Recorder()
        # Start recording
        msg.record = menu
        # Save current recording
        msg.save = btn_y
        # Clear current recording
        msg.clear = btn_x
        self.record_msg = msg

def deadband(var,band=0.2):
    var = max(-1.0,min(var,1.0))

    if var > band:
        return (var-band) / (1.0-band)

    if var < -band:
        return (var+band) / (1.0-band)
    return 0.0

if __name__ == "__main__":
    user_input = UserInput()
    user_input.spin()

