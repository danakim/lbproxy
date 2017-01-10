# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
# @author: Juliano Martinez (ncode)

from sqlalchemy.exc import IntegrityError

from .connection import connect_to_f5
from .db import models, db_utils
from .utils import (
    config, has_attr, get_logger
)
from .exceptions import (
    PoolMemberDoesNotExist, NodeDoesNotExist, OperationNotPermited
)


logger = get_logger()
session = db_utils.get_database_session()


class Device(object):
    def __init__(self, name, pool=None, partition=None):
        self.name = name
        self._pool = pool
        if pool:
            self._partition = '/{}'.format(pool.split('/')[1])
        else:
            self._partition = partition

    def exists(self):
        ss = session.query(models.PoolMember.device).filter_by(
            device=self.name,
        ).first()
        return True if ss else False

    @property
    def partition(self, partition):
        return self._partition

    @partition.setter
    def partition(self, partition):
        self._partition = partition

    @property
    def pool(self):
        return self._pool

    @pool.setter
    def pool(self, pool):
        self._pool = pool
        self._partition = '/{}'.format(pool.split('/')[1]) if pool else None

    def all_poolmembers(self):
        return {Poolmember(poolmember[0], device=self.name)
                for poolmember in session.query(
            models.PoolMember.nodename).filter_by(
            device=self.name).distinct().all()}

    def pools(self):
        return {Pool(pool[0], device=self.name) for pool in session.query(
            models.PoolMember.pool).filter_by(
            device=self.name).distinct().all()}

    @has_attr('_pool', 'You must select a pool first')
    def poolmembers(self):
        return {Poolmember(poolmember[0], pool=self._pool, device=self.name)
                for poolmember in session.query(
            models.PoolMember.nodename).filter_by(
            device=self.name, pool=self._pool).distinct().all()}

    def partitions(self):
        return {Partition(partition[0], device=self.name)
                for partition in session.query(
            models.PoolMember.partition).filter_by(
            device=self.name).distinct().all()}


class Partition(object):
    def __init__(self, name, device=None):
        if not name.startswith('/'):
            raise NameError('Invalid pool name')

        self.name = name
        self._device = device

    @property
    def device(self, device):
        return self._device

    @device.setter
    def device(self, device):
        self._device = device

    def all_pools(self):
        return {pool[0] for pool in session.query(
            models.PoolMember.pool).filter_by(
            partition=self.name).distinct().all()}

    def all_poolmembers(self, pool=None):
        if pool:
            return session.query(models.PoolMember.nodename).filter_by(
                partition=self.name, pool=pool).distinct().all()
        return session.query(models.PoolMember.nodenames).filter_by(
            partition=self.name).distinct(models.PoolMember.nodenames).all()

    @has_attr('_device', 'You must select a device first')
    def pools(self):
        return {Pool(pool[0], device=self._device)
                for pool in session.query(
            models.PoolMember.pool).filter_by(
            device=self._device, partition=self.name).distinct().all()}

    @has_attr('_device', 'You must select a device first')
    def poolmembers(self):
        return {Poolmember(poolmember[0], device=self._device)
                for poolmember in session.query(
            models.PoolMember.nodename).filter_by(
            device=self._device, partition=self.name).distinct().all()}

    def devices(self):
        return {Device(device[0]) for device in session.query(
            models.PoolMember.devices).filter_by(
            partition=self.name).distinct().all()}

    @has_attr('_device', 'You must select a device first')
    def exists(self):
        ss = session.query(models.PoolMember.partition).filter_by(
            device=self._device,
            partition=self.name,
        ).first()
        return True if ss else False

    @has_attr('_device', 'You must select a device first')
    def delete(self):
        session.begin(subtransactions=True)
        try:
            for ss in session.query(models.PoolMember).filter_by(
                    device=self._device, partition=self.name).all():
                session.delete(ss)
            session.commit()
        except Exception as err:
            session.rollback()
            raise Exception(err)
        logger.debug("Partition has been deleted: {}/{}/{}".format(
            self._device, self._partition, self.name
        ))
        return True


class Pool(object):
    def __init__(self, name, device=None):
        if not name.startswith('/'):
            raise NameError('Invalid pool name')

        self.name = name
        self._partition = "/%s" % name.split('/')[1]
        self._device = device

    def devices(self):
        return {Device(device[0], pool=self._pool)
                for device in session.query(
            models.PoolMember.device).filter_by(
            pool=self.name).distinct().all()}

    @has_attr('_device', 'You must select a device first')
    def exists(self):
        ss = session.query(models.PoolMember.pool).filter_by(
            device=self._device,
            pool=self.name,
        ).first()
        return True if ss else False

    def all_poolmembers(self):
        return {Poolmember(poolmember[0])
                for poolmember in session.query(
            models.PoolMember.nodename).filter_by(
            pool=self.name).distinct().all()}

    @has_attr('_device', 'You must select a device first')
    def poolmembers(self):
        return {Poolmember(poolmember[0], pool=self.name, device=self._device)
                for poolmember in session.query(
            models.PoolMember.nodename).filter_by(
            device=self._device, pool=self.name).distinct().all()}

    @has_attr('_device', 'You must select a device first')
    def delete(self):
        session.begin(subtransactions=True)
        try:
            for ss in session.query(models.PoolMember).filter_by(
                    device=self._device, pool=self.name).all():
                session.delete(ss)
            session.commit()
        except Exception as err:
            session.rollback()
            raise Exception(err)
        logger.debug("Pool has been deleted: {}/{}/{}".format(
            self._device, self._partition, self.name
        ))
        return True

    @property
    def device(self, device):
        return self._device

    @device.setter
    def device(self, device):
        self._device = device


class Poolmember(object):
    def __init__(self, name, pool=None, device=None):
        if not name.startswith('/'):
            raise NameError('Invalid pool name')

        self.name = name
        self._pool = pool
        self._device = device
        self._partition = '/{}'.format(pool.split('/')[1]) if pool else None
        self._skip_f5 = False

    @property
    def partition(self, partition):
        return self._partition

    @partition.setter
    def partition(self, partition):
        self._partition = partition

    @property
    def pool(self):
        return self._pool

    @pool.setter
    def pool(self, pool):
        self._pool = pool
        self._partition = '/{}'.format(pool.split('/')[1]) if pool else None

    @property
    def device(self, device):
        return self._device

    @device.setter
    def device(self, device):
        self._device = device

    @has_attr('_device', 'You must select a device first')
    @has_attr('_pool', 'You must select a pool first')
    def _exists(self):
        ss = session.query(models.PoolMember).filter_by(
            device=self._device,
            partition=self._partition,
            pool=self._pool,
            nodename=self.name
        )
        return ss.first() if ss else None

    @has_attr('_device', 'You must select a device first')
    @has_attr('_pool', 'You must select a pool first')
    def create(self, port, status):
        session.begin(subtransactions=True)
        try:
            session.add(models.PoolMember(
                device=self._device,
                partition=self._partition,
                pool=self._pool,
                nodename=self.name,
            ))
            session.commit()
        except IntegrityError:
            session.rollback()
            forbidden_msg = "Poolmember already exists: {}/{}/{}/{}".format(
                self._device, self._partition, self._pool, self.name
            )
            raise OperationNotPermited(forbidden_msg)
        except Exception as err:
            session.rollback()
            raise Exception(err)
        logger.debug("Poolmember has been created: {}/{}/{}/{}".format(
            self._device, self._partition, self._pool, self.name
        ))

        ss = self._exists()

        session.begin(subtransactions=True)
        try:
            session.add(models.PoolMemberProperty(
                poolmember_id=ss.id,
                port=port,
                status=status,
            ))
            session.commit()
        except IntegrityError:
            session.rollback()
            forbidden_msg = (
                "PoolMemberProperties already exists: {}/{}/{}/{}".format(
                    self._device, self._partition, self._pool, self.name
                ))
            raise OperationNotPermited(forbidden_msg)
        except Exception as err:
            session.rollback()
            raise Exception(err)
        logger.debug(
            "PoolMemberProperties have been created: {}/{}/{}/{}".format(
                self._device, self._partition, self._pool, self.name
            ))

    @has_attr('_device', 'You must select a device first')
    @has_attr('_pool', 'You must select a pool first')
    def delete(self):
        ss = self._exists()
        session.begin(subtransactions=True)
        try:
            session.delete(ss)
            session.commit()
        except Exception as err:
            session.rollback()
            raise Exception(err)
        logger.debug("Poolmember has been deleted: {}/{}/{}/{}".format(
            self._device, self._partition, self._pool, self.name
        ))
        return True

    def pools(self):
        return {Pool(pool[0]) for pool in session.query(
            models.PoolMember.pool).filter_by(
            nodename=self.name).distinct().all()}

    def devices(self):
        return {Device(device[0]) for device in session.query(
            models.PoolMember.device).filter_by(
            nodename=self.name).distinct().all()}

    def partitions(self):
        return {Partition(partition[0]) for partition in session.query(
            models.PoolMember.partition).filter_by(
            nodename=self.name).distinct().all()}

    @has_attr('_device', 'You must select a device first')
    @has_attr('_pool', 'You must select a pool first')
    def exists(self):
        ss = self._exists()
        return True if ss else False

    @has_attr('_device', 'You must select a device first')
    @has_attr('_pool', 'You must select a pool first')
    def port(self):
        ss = self._exists()
        if not ss:
            raise PoolMemberDoesNotExist(
                "Poolmember not found: {}/{}/{}/{}".format(
                    self._device, self._partition, self._pool, self.name
                )
            )

        st = session.query(models.PoolMemberProperty).filter_by(
            poolmember_id=ss.id).first()
        return st.port

    @property
    @has_attr('_device', 'You must select a device first')
    @has_attr('_pool', 'You must select a pool first')
    def enabled(self):
        ss = self._exists()
        if not ss:
            raise PoolMemberDoesNotExist(
                "Poolmember not found: {}/{}/{}/{}".format(
                    self._device, self._partition, self._pool, self.name
                )
            )

        st = session.query(models.PoolMemberProperty).filter_by(
            poolmember_id=ss.id).first()
        return st.status

    @enabled.setter
    @has_attr('_device', 'You must select a device first')
    @has_attr('_pool', 'You must select a pool first')
    def enabled(self, state):
        ss = self._exists()
        if not ss:
            raise PoolMemberDoesNotExist(
                "Poolmember not found: {}/{}/{}/{}".format(
                    self._device, self._partition, self._pool, self.name
                )
            )

        st = session.query(models.PoolMemberProperty
                           ).filter_by(poolmember_id=ss.id).first()
        session.begin(subtransactions=True)
        try:
            st.status = True
            session.commit()

            if not self._skip_f5:
                asasaa
                lb = connect_to_f5(self._device)
                pm = lb.pm_get(
                    lb.node_get(self.name),
                    self.port(),
                    lb.pool_get(self._pool)
                )
                pm.enabled = state

        except Exception as err:
            session.rollback()
            raise Exception(err)
        logger.debug("Poolmember has been enabled: {}/{}/{}/{}".format(
            self._device, self._partition, self._pool, self.name
        ))

    @property
    def skip_f5(self):
        return self._skip_f5

    @skip_f5.setter
    def skip_f5(self, value):
        self._skip_f5 = value


class Node(object):
    def __init__(self, name, device=None):
        if not name.startswith('/'):
            raise NameError('Invalid pool name')

        self.name = name
        self._device = device
        self._skip_f5 = False

    @property
    def device(self, device):
        return self._device

    @device.setter
    def device(self, device):
        self._device = device

    @has_attr('_device', 'You must select a device first')
    def _exists(self):
        ss = session.query(models.PoolMember).filter_by(
            device=self._device,
            nodename=self.name
        )
        return ss.first() if ss else None

    def pools(self):
        return {Pool(pool[0]) for pool in session.query(
            models.PoolMember.pool).filter_by(
            nodename=self.name).distinct().all()}

    def devices(self):
        return {Device(device[0]) for device in session.query(
            models.PoolMember.device).filter_by(
            nodename=self.name).distinct().all()}

    def partitions(self):
        return {Partition(partition[0]) for partition in session.query(
            models.PoolMember.partition).filter_by(
            nodename=self.name).distinct().all()}

    @has_attr('_device', 'You must select a device first')
    def exists(self):
        ss = self._exists()
        return True if ss else False

    @property
    @has_attr('_device', 'You must select a device first')
    def enabled(self):
        ss = self._exists()
        if not ss:
            raise NodeDoesNotExist(
                "Node not found: {}/{}/{}/{}".format(
                    self._device, self.name
                )
            )

        lb = connect_to_f5(self._device)
        nd = lb.node_get(self.name)
        return nd.enabled

    @enabled.setter
    @has_attr('_device', 'You must select a device first')
    def enabled(self, state):
        ss = self._exists()
        if not ss:
            raise NodeDoesNotExist(
                "Node not found: {}/{}".format(
                    self._device, self.name
                )
            )

        pm = Poolmember(self.name, self._device)
        pm.skip_f5 = self.skip_f5

        for pool in pm.pools():
            pm.pool = pool.name
            pm.enabled = state

        lb = connect_to_f5(self._device)
        nd = lb.node_get(self.name)
        nd.enabled = state

    @property
    def skip_f5(self):
        return self._skip_f5

    @skip_f5.setter
    def skip_f5(self, value):
        self._skip_f5 = value
