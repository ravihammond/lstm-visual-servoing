
(cl:in-package :asdf)

(defsystem "lstm_visual_servoing-msg"
  :depends-on (:roslisp-msg-protocol :roslisp-utils :std_msgs-msg
)
  :components ((:file "_package")
    (:file "Control" :depends-on ("_package_Control"))
    (:file "_package_Control" :depends-on ("_package"))
    (:file "Recorder" :depends-on ("_package_Recorder"))
    (:file "_package_Recorder" :depends-on ("_package"))
  ))