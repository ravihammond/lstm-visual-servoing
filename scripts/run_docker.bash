n_cores=$(grep -c ^processor /proc/cpuinfo)
avail_cores=$(($n_cores - 4))
if [ $avail_cores -lt 4 ]
then
        avail_cores=4
fi
cpus=$avail_cores
mem="24g"

# XServer
xsock="/tmp/.X11-unix"
xauth="/tmp/.docker.xauth"

docker run -it \
    --user=root \
    --privileged \
    --env="DISPLAY"=$DISPLAY \
    --volume="/etc/group:/etc/group:ro"   \
    --volume="/etc/passwd:/etc/passwd:ro" \
    --volume="/etc/shadow:/etc/shadow:ro" \
    --volume=$(pwd)/catkin_ws:/root/catkin_ws:rw \
    --volume=$(pwd)/scripts/docker_resources/setup_script.bash:/root/setup_script.bash \
    --volume=$xsock:$xsock:rw \
    --volume=$xauth:$xauth:rw \
    --env=XAUTHORITY=$xauth \
    --device=/dev \
    --network=host \
    --workdir=/root/catkin_ws \
    --cpus=$cpus \
    --memory=$mem \
    --gpus all \
    lstm-visual-servoing 

# IP: 10.90.184.11
#--volume="/dev:/dev" \
