build-ros: 
	docker build -t cuda-ros-noetic-desktop-full -f dockerfiles/Dockerfile.cudaros .

build: 
	docker build -t lstm-visual-servoing -f dockerfiles/Dockerfile.project .

run:
	xhost +
	bash scripts/run_docker.bash

# RUN sh -c 'echo "deb http://packages.ros.org/ros/ubuntu focal main" > /etc/apt/sources.list.d/ros-focal.list'
# RUN apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654

# RUN apt-get update && apt-get install -y \
    ros-noetic-desktop-full 
