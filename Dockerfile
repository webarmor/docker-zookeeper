# Dockerfile for ZooKeeper
# Based on git@github.com:signalfuse/docker-zookeeper.git
# MAINTAINER Maxime Petazzoni <max@signalfuse.com>

FROM webarmor/common
MAINTAINER Webarmor <devops@immun.io>

# Get latest stable release of ZooKeeper
RUN wget -q -O - http://archive.immun.io.s3.amazonaws.com/zookeeper-3.4.6.tar.gz \
  | tar -C /opt -xz

RUN pip install maestro==0.2.0
ADD run.py /opt/zookeeper-3.4.6/.docker/

WORKDIR /opt/zookeeper-3.4.6/
CMD ["python", "/opt/zookeeper-3.4.6/.docker/run.py"]
