from sqlalchemy.orm import sessionmaker
from lbproxy.db import models

_engine = models.engine
_maker = None


def get_database_session(autocommit=True, expire_on_commit=False):
    global _maker, _engine
    if not _maker:
        assert _engine
        _maker = sessionmaker(bind=_engine,
                              autocommit=autocommit,
                              expire_on_commit=expire_on_commit)
    return _maker()


def unregister_database_models(base):
    global _engine
    assert _engine
    base.metadata.drop_all(_engine)
