; Auto-generated. Do not edit!


(cl:in-package lstm_visual_servoing-msg)


;//! \htmlinclude Recorder.msg.html

(cl:defclass <Recorder> (roslisp-msg-protocol:ros-message)
  ((header
    :reader header
    :initarg :header
    :type std_msgs-msg:Header
    :initform (cl:make-instance 'std_msgs-msg:Header))
   (record
    :reader record
    :initarg :record
    :type cl:boolean
    :initform cl:nil)
   (save
    :reader save
    :initarg :save
    :type cl:boolean
    :initform cl:nil)
   (clear
    :reader clear
    :initarg :clear
    :type cl:boolean
    :initform cl:nil))
)

(cl:defclass Recorder (<Recorder>)
  ())

(cl:defmethod cl:initialize-instance :after ((m <Recorder>) cl:&rest args)
  (cl:declare (cl:ignorable args))
  (cl:unless (cl:typep m 'Recorder)
    (roslisp-msg-protocol:msg-deprecation-warning "using old message class name lstm_visual_servoing-msg:<Recorder> is deprecated: use lstm_visual_servoing-msg:Recorder instead.")))

(cl:ensure-generic-function 'header-val :lambda-list '(m))
(cl:defmethod header-val ((m <Recorder>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader lstm_visual_servoing-msg:header-val is deprecated.  Use lstm_visual_servoing-msg:header instead.")
  (header m))

(cl:ensure-generic-function 'record-val :lambda-list '(m))
(cl:defmethod record-val ((m <Recorder>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader lstm_visual_servoing-msg:record-val is deprecated.  Use lstm_visual_servoing-msg:record instead.")
  (record m))

(cl:ensure-generic-function 'save-val :lambda-list '(m))
(cl:defmethod save-val ((m <Recorder>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader lstm_visual_servoing-msg:save-val is deprecated.  Use lstm_visual_servoing-msg:save instead.")
  (save m))

(cl:ensure-generic-function 'clear-val :lambda-list '(m))
(cl:defmethod clear-val ((m <Recorder>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader lstm_visual_servoing-msg:clear-val is deprecated.  Use lstm_visual_servoing-msg:clear instead.")
  (clear m))
(cl:defmethod roslisp-msg-protocol:serialize ((msg <Recorder>) ostream)
  "Serializes a message object of type '<Recorder>"
  (roslisp-msg-protocol:serialize (cl:slot-value msg 'header) ostream)
  (cl:write-byte (cl:ldb (cl:byte 8 0) (cl:if (cl:slot-value msg 'record) 1 0)) ostream)
  (cl:write-byte (cl:ldb (cl:byte 8 0) (cl:if (cl:slot-value msg 'save) 1 0)) ostream)
  (cl:write-byte (cl:ldb (cl:byte 8 0) (cl:if (cl:slot-value msg 'clear) 1 0)) ostream)
)
(cl:defmethod roslisp-msg-protocol:deserialize ((msg <Recorder>) istream)
  "Deserializes a message object of type '<Recorder>"
  (roslisp-msg-protocol:deserialize (cl:slot-value msg 'header) istream)
    (cl:setf (cl:slot-value msg 'record) (cl:not (cl:zerop (cl:read-byte istream))))
    (cl:setf (cl:slot-value msg 'save) (cl:not (cl:zerop (cl:read-byte istream))))
    (cl:setf (cl:slot-value msg 'clear) (cl:not (cl:zerop (cl:read-byte istream))))
  msg
)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql '<Recorder>)))
  "Returns string type for a message object of type '<Recorder>"
  "lstm_visual_servoing/Recorder")
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'Recorder)))
  "Returns string type for a message object of type 'Recorder"
  "lstm_visual_servoing/Recorder")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql '<Recorder>)))
  "Returns md5sum for a message object of type '<Recorder>"
  "f146743ee93cda48244d1ec7146e2e0b")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql 'Recorder)))
  "Returns md5sum for a message object of type 'Recorder"
  "f146743ee93cda48244d1ec7146e2e0b")
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql '<Recorder>)))
  "Returns full string definition for message of type '<Recorder>"
  (cl:format cl:nil "Header header~%bool record~%bool save~%bool clear~%~%================================================================================~%MSG: std_msgs/Header~%# Standard metadata for higher-level stamped data types.~%# This is generally used to communicate timestamped data ~%# in a particular coordinate frame.~%# ~%# sequence ID: consecutively increasing ID ~%uint32 seq~%#Two-integer timestamp that is expressed as:~%# * stamp.sec: seconds (stamp_secs) since epoch (in Python the variable is called 'secs')~%# * stamp.nsec: nanoseconds since stamp_secs (in Python the variable is called 'nsecs')~%# time-handling sugar is provided by the client library~%time stamp~%#Frame this data is associated with~%string frame_id~%~%~%"))
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql 'Recorder)))
  "Returns full string definition for message of type 'Recorder"
  (cl:format cl:nil "Header header~%bool record~%bool save~%bool clear~%~%================================================================================~%MSG: std_msgs/Header~%# Standard metadata for higher-level stamped data types.~%# This is generally used to communicate timestamped data ~%# in a particular coordinate frame.~%# ~%# sequence ID: consecutively increasing ID ~%uint32 seq~%#Two-integer timestamp that is expressed as:~%# * stamp.sec: seconds (stamp_secs) since epoch (in Python the variable is called 'secs')~%# * stamp.nsec: nanoseconds since stamp_secs (in Python the variable is called 'nsecs')~%# time-handling sugar is provided by the client library~%time stamp~%#Frame this data is associated with~%string frame_id~%~%~%"))
(cl:defmethod roslisp-msg-protocol:serialization-length ((msg <Recorder>))
  (cl:+ 0
     (roslisp-msg-protocol:serialization-length (cl:slot-value msg 'header))
     1
     1
     1
))
(cl:defmethod roslisp-msg-protocol:ros-message-to-list ((msg <Recorder>))
  "Converts a ROS message object to a list"
  (cl:list 'Recorder
    (cl:cons ':header (header msg))
    (cl:cons ':record (record msg))
    (cl:cons ':save (save msg))
    (cl:cons ':clear (clear msg))
))
