#!/usr/bin/env python

# base on Copyright (C) 2013 SignalFuse, Inc.

# Start script for the ZooKeeper service.
from __future__ import print_function

import os
import sys
import subprocess

os.chdir(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..'))

ZOOKEEPER_CONFIG_FILE = os.path.join('conf', 'zoo.cfg')
ZOOKEEPER_LOG_CONFIG_FILE = os.path.join('conf', 'log4j.properties')
ZOOKEEPER_DATA_DIR = '/var/lib/zookeeper'
ZOOKEEPER_NODE_ID = None
DOCKER_HOST = os.environ.get('DOCKER_HOST')
DOCKER_ENV = os.environ.get('DOCKER_ENV', 'development')
JMX_PORT = os.environ.get('JMX_PORT', -1)
LOG_PATTERN = ("%d{ISO8601} [myid:%X{myid}] - %-5p [%t:%C{1}@%L] - %m%n")

servers = None
# Build the ZooKeeper node configuration.
conf = {
    'tickTime': 2000,
    'initLimit': 10,
    'syncLimit': 5,
    'dataDir': ZOOKEEPER_DATA_DIR,
    'clientPort': os.environ.get('ZK_CLIENT_PORT', 2181),
    'quorumListenOnAllIPs': True,
    'autopurge.snapRetainCount':
        int(os.environ.get('MAX_SNAPSHOT_RETAIN_COUNT', 10)),
    'autopurge.purgeInterval':
        int(os.environ.get('PURGE_INTERVAL', 24)),
}


def build_node_repr(node):
    """Build the representation of a node with peer and leader-election
    ports."""

    host = get_ipaddress if node == DOCKER_HOST else node
    return '{}:2888:3888'.format(host)

def get_ipaddress():
    return run_cmd(["hostname", "-i"])

def get_hostname():
    return run_cmd(["hostname"])

def run_cmd(cmdargs):
    proc = subprocess.Popen(cmdargs, stdout=subprocess.PIPE)
    return proc.communicate()[0].split()

# Add the ZooKeeper node list with peer and leader election ports and figure
# out our own ID. ZOOKEEPER_SERVER_IDS contains a comma-separated list of
# node:id tuples describing the server ID of each node in the cluster, by its
# container name. If not specified, we assume single-node mode.
zk_servers = os.environ.get('ZOOKEEPER_SERVER_IDS')
if zk_servers and DOCKER_HOST:
    servers = os.environ['ZOOKEEPER_SERVER_IDS'].split(',')

    for server in servers:
        node, id = server.split(':')
        conf['server.{}'.format(id)] = build_node_repr(node)
        # Duplicate condition ok for now
        if node == DOCKER_HOST:
            ZOOKEEPER_NODE_ID = id

# Write out the ZooKeeper configuration file.
with open(ZOOKEEPER_CONFIG_FILE, 'w+') as f:
    for entry in conf.iteritems():
        f.write("%s=%s\n" % entry)

# Setup the logging configuration.
with open(ZOOKEEPER_LOG_CONFIG_FILE, 'w+') as f:
    f.write("""# Log4j configuration, logs to rotating file
log4j.rootLogger=INFO,R

log4j.appender.R=org.apache.log4j.RollingFileAppender
log4j.appender.R.File=/var/log/zk/zk_%s.log
log4j.appender.R.MaxFileSize=100MB
log4j.appender.R.MaxBackupIndex=10
log4j.appender.R.layout=org.apache.log4j.PatternLayout
log4j.appender.R.layout.ConversionPattern=%s
""" % (ZOOKEEPER_NODE_ID, LOG_PATTERN))

# Set cluster size here
ZOOKEEPER_CLUSTER_SIZE = len(servers) if servers else 1

# Write out the 'myid' file in the data directory if in cluster mode.
if ZOOKEEPER_NODE_ID:
    if not os.path.exists(ZOOKEEPER_DATA_DIR):
        os.makedirs(ZOOKEEPER_DATA_DIR, mode=0750)
    with open(os.path.join(ZOOKEEPER_DATA_DIR, 'myid'), 'w+') as f:
        f.write('%s\n' % ZOOKEEPER_NODE_ID)
    sys.stderr.write(
        'Starting zookeeper, node id#{} of a {}-node ZooKeeper cluster...\n'
        .format(ZOOKEEPER_NODE_ID,
                ZOOKEEPER_CLUSTER_SIZE))
else:
    sys.stderr.write('Starting zookeeper as a single-node ZooKeeper cluster...\n')

jvmflags = [
    '-server',
    '-showversion',
    '-Dvisualvm.display.name="{}/zookeeper-{}"'.format(
        DOCKER_ENV, ZOOKEEPER_NODE_ID)
]

if JMX_PORT != -1:
    jvmflags += [
        '-Djava.rmi.server.hostname={}'.format(get_hostname()),
        '-Dcom.sun.management.jmxremote.port={}'.format(JMX_PORT),
        '-Dcom.sun.management.jmxremote.rmi.port={}'.format(JMX_PORT),
        '-Dcom.sun.management.jmxremote.authenticate=false',
        '-Dcom.sun.management.jmxremote.local.only=false',
        '-Dcom.sun.management.jmxremote.ssl=false',
    ]

os.environ['JVMFLAGS'] = ' '.join(jvmflags) + os.environ.get('JVM_OPTS', '')

# Start ZooKeeper
os.execl('bin/zkServer.sh', 'zookeeper', 'start-foreground')
