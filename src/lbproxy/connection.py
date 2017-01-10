import socket

import f5

from .utils import config, get_logger
from .exceptions import F5ConnectionError, F5HostNotFound


logger = get_logger()

# Read the F5 username and password
f5_admin = config.get('f5', 'username')
f5_admin_pass = config.get('f5', 'password')

# A function that connects to the given F5 or reuses old connections
f5_list = {}


def open_connection(loadbalancer):
    try:
        f5_list.update(
            {loadbalancer: f5.Lb(loadbalancer, f5_admin, f5_admin_pass)}
        )
    except socket.gaierror:
        raise F5HostNotFound(
            "Could not resolve {}. Please try again.".format(loadbalancer)
        )
    except Exception as err:
        raise F5ConnectionError(
            "Could not connect to {}. Please try again. {}".format(
                loadbalancer, repr(err)
            )
        )


def connect_to_f5(loadbalancer):
    if loadbalancer in f5_list:
        try:
            f5_list[loadbalancer].failover_state
        except:
            open_connection(loadbalancer)
        return f5_list[loadbalancer]
    else:
        open_connection(loadbalancer)
        return f5_list[loadbalancer]
