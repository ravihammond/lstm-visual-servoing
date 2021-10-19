;; Auto-generated. Do not edit!


(when (boundp 'lstm_visual_servoing::Recorder)
  (if (not (find-package "LSTM_VISUAL_SERVOING"))
    (make-package "LSTM_VISUAL_SERVOING"))
  (shadow 'Recorder (find-package "LSTM_VISUAL_SERVOING")))
(unless (find-package "LSTM_VISUAL_SERVOING::RECORDER")
  (make-package "LSTM_VISUAL_SERVOING::RECORDER"))

(in-package "ROS")
;;//! \htmlinclude Recorder.msg.html
(if (not (find-package "STD_MSGS"))
  (ros::roseus-add-msgs "std_msgs"))


(defclass lstm_visual_servoing::Recorder
  :super ros::object
  :slots (_header _record _save _clear ))

(defmethod lstm_visual_servoing::Recorder
  (:init
   (&key
    ((:header __header) (instance std_msgs::Header :init))
    ((:record __record) nil)
    ((:save __save) nil)
    ((:clear __clear) nil)
    )
   (send-super :init)
   (setq _header __header)
   (setq _record __record)
   (setq _save __save)
   (setq _clear __clear)
   self)
  (:header
   (&rest __header)
   (if (keywordp (car __header))
       (send* _header __header)
     (progn
       (if __header (setq _header (car __header)))
       _header)))
  (:record
   (&optional (__record :null))
   (if (not (eq __record :null)) (setq _record __record)) _record)
  (:save
   (&optional (__save :null))
   (if (not (eq __save :null)) (setq _save __save)) _save)
  (:clear
   (&optional (__clear :null))
   (if (not (eq __clear :null)) (setq _clear __clear)) _clear)
  (:serialization-length
   ()
   (+
    ;; std_msgs/Header _header
    (send _header :serialization-length)
    ;; bool _record
    1
    ;; bool _save
    1
    ;; bool _clear
    1
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; std_msgs/Header _header
       (send _header :serialize s)
     ;; bool _record
       (if _record (write-byte -1 s) (write-byte 0 s))
     ;; bool _save
       (if _save (write-byte -1 s) (write-byte 0 s))
     ;; bool _clear
       (if _clear (write-byte -1 s) (write-byte 0 s))
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; std_msgs/Header _header
     (send _header :deserialize buf ptr-) (incf ptr- (send _header :serialization-length))
   ;; bool _record
     (setq _record (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;; bool _save
     (setq _save (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;; bool _clear
     (setq _clear (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;;
   self)
  )

(setf (get lstm_visual_servoing::Recorder :md5sum-) "f146743ee93cda48244d1ec7146e2e0b")
(setf (get lstm_visual_servoing::Recorder :datatype-) "lstm_visual_servoing/Recorder")
(setf (get lstm_visual_servoing::Recorder :definition-)
      "Header header
bool record
bool save
bool clear

================================================================================
MSG: std_msgs/Header
# Standard metadata for higher-level stamped data types.
# This is generally used to communicate timestamped data 
# in a particular coordinate frame.
# 
# sequence ID: consecutively increasing ID 
uint32 seq
#Two-integer timestamp that is expressed as:
# * stamp.sec: seconds (stamp_secs) since epoch (in Python the variable is called 'secs')
# * stamp.nsec: nanoseconds since stamp_secs (in Python the variable is called 'nsecs')
# time-handling sugar is provided by the client library
time stamp
#Frame this data is associated with
string frame_id

")



(provide :lstm_visual_servoing/Recorder "f146743ee93cda48244d1ec7146e2e0b")


