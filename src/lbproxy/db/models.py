import datetime

from sqlalchemy import (
    create_engine, event,
    Boolean, Column, Date, Integer, String,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool

from lbproxy.utils import config

Base = declarative_base()


class PoolMember(Base):
    __tablename__ = 'poolmembers'
    __table_args__ = (UniqueConstraint(
        'device', 'partition', 'pool',
        'nodename', name='_pm_mapping'),
                      {'mysql_engine': 'InnoDB'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    device = Column(String(100), nullable=False)
    partition = Column(String(100), nullable=False)
    pool = Column(String(100), nullable=False)
    nodename = Column(String(100), nullable=False)
    created_at = Column(Date, default=datetime.datetime.now)
    updated_at = Column(Date, onupdate=datetime.datetime.now)
    poolmemberproperty = relationship(
        'PoolMemberProperty', cascade='all,delete', backref='poolmembers'
    )

    def __init__(self, device, partition, pool, nodename):
        self.device = device
        self.partition = partition
        self.pool = pool
        self.nodename = nodename

    def __repr__(self):
        return "<Poolmember('%s','%s','%s','%s')>" % (
            self.device, self.partition,
            self.pool, self.nodename
        )


class PoolMemberProperty(Base):
    __tablename__ = 'poolmember_properties'
    __table_args__ = (UniqueConstraint(
        'poolmember_id', 'port', name='_pmid_mapping'),
                      {'mysql_engine': 'InnoDB'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    poolmember_id = Column(Integer, ForeignKey('poolmembers.id'),
                           nullable=False)
    port = Column(Integer, nullable=False)
    status = Column(Boolean, nullable=False)
    created_at = Column(Date, default=datetime.datetime.now)
    updated_at = Column(Date, onupdate=datetime.datetime.now)

    def __init__(self, poolmember_id, port, status):
        self.poolmember_id = poolmember_id
        self.port = port
        self.status = status

    def __repr__(self):
        return "<PoolMemberProperty('%s','%s','%s')>" % (
            self.poolmember.nodename, self.port, self.status
        )


database_type = config.get('lbproxyd', 'database_type')
database_name = config.get('lbproxyd', 'database_name')

engine = None
if 'sqlite' in database_type:
    def _fk_pragma_on_connect(dbapi_con, con_record):
        dbapi_con.execute('pragma foreign_keys=ON')

    engine = create_engine('%s:///%s' % (database_type, database_name))
    event.listen(engine, 'connect', _fk_pragma_on_connect)
else:
    database_user = config.get('lbproxyd', 'database_user')
    database_pass = config.get('lbproxyd', 'database_pass')
    database_host = config.get('lbproxyd', 'database_host')
    engine = create_engine("%s://%s:%s@%s/%s" % (database_type,
                                                 database_user,
                                                 database_pass,
                                                 database_host,
                                                 database_name),
                           poolclass=NullPool)

Base.metadata.create_all(engine)
