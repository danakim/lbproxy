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

import copy
import configparser
import hashlib
import inspect
import json
import os
import re
import socket
import syslog
from functools import wraps
from io import TextIOWrapper

import redis
from bottle import response, request, abort
from .exceptions import (
    NotSelected
)
from redis.sentinel import Sentinel


logger = None
caller = inspect.stack()[-1][1].split('/')[-1]

config = configparser.SafeConfigParser()
config_file = "/etc/lbproxy/lbproxy.cfg"

if os.path.isfile(config_file):
    config.read(config_file)


class StdOutAndErrWapper(object):
    def write(self, data):
        if '\n' in data:
            for line in data.split('\n'):
                logger.info(re.sub(
                    '(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)',
                    request.get_header('X-Real-IP'), line))
        else:
            logger.info(str(re.sub(
                '(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)',
                request.get_header('X-Real-IP'), line)).strip())


class SyslogWrapper(object):
    def __init__(self, config=None):
        self.config = config

    def info(self, msg):
        syslog.syslog(syslog.LOG_INFO, msg)

    def warning(self, msg):
        syslog.syslog(syslog.LOG_WARNING, msg)

    def critical(self, msg):
        syslog.syslog(syslog.LOG_CRIT, msg)

    def error(self, msg):
        syslog.syslog(syslog.LOG_ERR, msg)

    def debug(self, msg):
        if self.config.has_section(caller) and \
                self.config.getboolean(caller, 'debug'):
            print(msg)
            syslog.syslog(syslog.LOG_DEBUG, msg)


def cache_call(f):
    @wraps(f)
    def caching(*args, **kwargs):
        try:
            ro = get_redis()
            rw = get_redis(write=True)
            _hash = "%s-%s" % (f.__name__, hashlib.md5("%s%s" % (
                repr(args),
                repr(kwargs)
            )).hexdigest())
            logger.debug('Trying to read result for %s from cache' % str(f))
            cache = ro.get(_hash)
            if not cache:
                logger.debug('No cache found for %s' % str(f))
                cache = json.dumps(f(*args, **kwargs))
                logger.debug('Caching result for %s' % str(f))
                rw.set(_hash, cache)
                rw.expire(_hash, config.getint('lbproxyd', 'redis_ttl'))
            logger.debug('Returning result for %s from cache' % str(f))
            return json.loads(cache)
        except Exception as e:
            logger.error(
                'Making a call without cache, cache '
                'call from %s failed with: %s' % (str(f), e.__str__)
            )
            return f(*args, **kwargs)

    return caching


def get_logger():
    global logger
    global config
    if logger: return logger
    syslog.openlog(caller, syslog.LOG_PID, syslog.LOG_DAEMON)
    logger = SyslogWrapper(config)
    return logger


def get_redis(write=False):
    if config.getboolean('lbproxyd', 'redis_is_sentinel'):
        port = config.getint('lbproxyd', 'redis_port')
        hosts = [(host, port) for host in
                 config.get('lbproxyd', 'redis_host').split()]

        sentinel = Sentinel(
            hosts, socket_timeout=5,
            decode_responses=True
        )
        if write:
            return sentinel.master_for('beam')
        else:
            return sentinel.slave_for('beam')
    else:
        r = redis.Redis(
            host=config.get('lbproxyd', 'redis_host'),
            port=config.getint('lbproxyd', 'redis_port'),
            db=config.getint('lbproxyd', 'redis_db'),
            decode_responses=True
        )
        return r


def handle_auth(f):
    @wraps(f)
    def authenticate(*args, **kwargs):
        if not config.getboolean('lbproxyd', 'authentication'):
            return f(*args, **kwargs)
        authentication_plugin = config.get(
            'authentication', 'authentication_plugin'
        )
        auth = load_auth_plugin(authentication_plugin)
        if auth.do(request):
            return f(*args, **kwargs)
        else:
            abort(403, 'Access denied')

    return authenticate


def load_auth_plugin(plugin):
    logger.debug('Loading authentication plug-in %s' % plugin)
    _module_ = 'lbproxy.auth.%s' % plugin
    module = __import__(_module_)
    module = getattr(module.auth, plugin)
    return module.Auth()


def reply_json(f):
    @wraps(f)
    def json_dumps(*args, **kwargs):
        r = f(*args, **kwargs)
        response.content_type = 'application/json; charset=UTF-8'
        if r and type(r) in (dict, list, tuple):
            return json.dumps(r)
        if r and type(r) is str:
            return r

    return json_dumps


def validate_loadbalancer_host(f):
    @wraps(f)
    def validate(*args, **kwargs):
        try:
            socket.gethostbyname(kwargs['loadbalancer'])
        except Exception as err:
            msg = "Invalid loadbalancer: {}".format(kwargs['loadbalancer'])
            logger.error("{} - Exception: {}".format(msg, err.__repr__()))
            abort(404, msg)
        return f(*args, **kwargs)

    return validate


def validate_shortcut_input(f):
    @wraps(f)
    def validate(*args, **kwargs):
        data = json.load(TextIOWrapper(copy.copy(request.body)))
        logger.debug(
            'Data %s received from request on %s' % (f.__name__, data))
        if not data:
            raise abort(400, 'No data received')

        enabled = data.get('enabled', None)
        disabled = data.get('disabled', None)

        if not isinstance(enabled, list) and not isinstance(disabled, list):
            abort(400, ('Error: unknown data type, '
                        'enabled or disabled must be list'))
        if not enabled and not disabled:
            abort(400, 'Error: enabled or disabled have to have some content')

        intersection = set(data['enabled']) & set(data['disabled'])
        if len(intersection) != 0:
            abort(409, ('Error: enabled and disabled must not'
                        ' have the same members [{}]'.format(intersection)))

        return f(*args, **kwargs)

    return validate


def validate_cache(f):
    @wraps(f)
    def validate(*args, **kwargs):
        r = get_redis()
        if not r.exists('beam::lbproxy::cache_warm'):
            abort(409, 'Server is not ready yet, try again later')
        return f(*args, **kwargs)

    return validate


def has_attr(src, msg):
    def wrapper(f):
        @wraps(f)
        def _decorator(self, *args, **kwargs):
            state = getattr(self, src)
            if state == None:
                raise NotSelected(msg)
            return f(self, *args, **kwargs)

        return _decorator

    return wrapper


# Try to get a config value, return default if it doesn't exist
def get_config(section, key, default=None, parser=config, cast=None):
    try:
        val = parser.get(section, key)
    except configparser.NoOptionError:
        return default
    except:
        raise

    if cast is not None:
        val = cast(val)

    return val
