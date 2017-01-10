# Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
# @author: Juliano Martinez (ncode)
# @author: Dan Achim (dan@hostatic.ro)

from .utils import (
    config, get_logger, get_redis
)

from . import Device, Poolmember, Partition, Pool

logger = get_logger()
ttl = config.get('lbproxyd', 'redis_ttl')


def cache_virtualserver(device, virtualservers):
    """Create and manage the cache namespaces for virtualservers"""
    logger.debug('Caching virtualservers data from %s' % device)
    r = get_redis(write=True)
    pipe = r.pipeline()
    nsd = 'device::virtualservers::%s' % device
    nsvsm = 'virtualserver::members'

    _vs = []
    for virtualserver, address in virtualservers:
        logger.debug('Caching data from virtualserver %s' % virtualserver)
        nsv = 'virtualserver::%s' % virtualserver
        nsvip = 'virtualserver::ip::%s::%s' % (device, virtualserver)
        pipe.sadd(nsd, virtualserver)
        pipe.sadd(nsv, device)
        pipe.set(nsvip, address)
        _vs.append(virtualserver)

    for virtualserver in (r.smembers(nsd) - set(_vs)):
        logger.debug('Cleaning data from virtualserver %s' % virtualserver)
        nsv = 'virtualserver::%s' % virtualserver
        nsvip = 'virtualserver::ip::%s::%s' % (device, virtualserver)
        pipe.srem(nsd, virtualserver)
        pipe.srem(nsv, device)
        pipe.delete(nsvip)

    pipe.execute()
    del _vs
    del virtualservers


def partitions(device, partitions):
    """Create and manage the cache namespaces for partitions"""
    logger.debug('Caching partitions data from %s' % device)
    device = Device(device)

    for partition in device.partitions():
        logger.info('Cleaning data from partition %s' % partition)
        if partition.name not in partitions:
            partition.delete()

def pools(device, pools):
    """Create and manage the cache namespaces for pools"""
    logger.debug('Caching pools from %s' % device)
    device = Device(device)

    for pool in device.pools():
        logger.info('Cleaning data from pool %s' % pool)
        if pool.name not in pools:
           pool.delete()

def poolmembers(device, pool, _poolmembers, failover_state):
    """Create and manage the cache namespaces for poolmembers"""
    logger.info('Caching poolmembers data from %s->%s' % (device, pool))
    active_poolmembers = set()
    device = Device(device, pool=pool)

    for poolmember, port, enabled in _poolmembers:
        logger.info('Caching data from poolmember %s' % poolmember)
        pm = Poolmember(poolmember, pool, device.name)
        if pm.exists():
            pm.skip_f5 = True
            pm.enabled = enabled
        else:
            pm.create(port, enabled)
        active_poolmembers.add(poolmember)

    for poolmember in device.poolmembers():
        logger.info('Cleaning data from poolmember %s' % poolmember)
        if poolmember.name not in active_poolmembers:
            poolmember.delete()

def cache_orphans(device, nodes):
    """Create and manage the cache namespaces for nodes without pool"""
    logger.debug('Checking for orphaned nodes on %s' % device)
    r = get_redis(write=True)
    pipe = r.pipeline()
    nsd = 'device::orphans::%s' % device
    _device = Device(device, r)

    pms = list()
    orphans = list()
    for pool in _device.pools():
        _device.select_pool(pool)
        for member in _device.poolmembers():
            pms.append(member)

    for node in nodes:
        if node.name not in pms:
            pipe.sadd(nsd, node)
            orphans.append(node)

    for orphan in (r.smembers(nsd) - set(orphans)):
        logger.debug('Cleaning data from orphan %s' % orphan)
        pipe.srem(nsd, orphan)

    pipe.execute()
    del pms
    del nodes
    del orphans
