# What is Lbproxy?

Lbproxy is a controller for loadbalancers. Its concept is to aggregate various
loadbalancers behind a single restful endpoint which will significantly simplify
object management from the application developer’s point of view.

It currently only supports F5 load balancers.

Lbproxy will enable the application developer to:

- abstract vendors
- abstract api versions
- test new vendors or solutions without changing anything internally
- add monitoring faster
- detect machines in wrong state faster
- very quickly query object states and relevant information
- integrate internal services in a painless way

## How does it work?

Lbproxy collects and maintains a cached representation of all loadbalancer data.
Queries are resolved quickly by fetching data from the local cache. Lbproxy
periodically updates this cached data store to ensure data is up to date.
Write operations are synchronously executed (write-through cache).

## How does Lbproxy knows where to write the changes?

Lbproxy has mapped all relations between Partitions, Pools, Pool Members,
Virtual Servers.

## How is it set up?

Lbproxy is a Python + bottle framework daemon.
To communicate with the F5s via their SOAP API it uses the (awesome) [python F5
library](https://github.com/tdevelioglu/python-f5).

## Limitations

Bypassing lbproxy by making changes directly on the appliances themselves can
lead to inconsistent results due to cache incoherency.

## Authentication headers

All your requests have to have the following headers:

    "X-Beam-User:<user>"
    "X-Beam-Key:<key>"
    "Content-Type: application/json"

## The following endpoints are available:

### Shortcuts

These are 'special' endpoints to be used by the developers to make their life
easier. They don't require you to know much about the objects you are modifying,
especially things like loadbalancers the objects live on. They try to autodetect
as much as possible for you, which might make things slow sometimes.

Endpoint:

    @get /v1/shortcut/node

What does it do:
    Returns a list of nodes' statuses in pools

How does a request look like:

    GET /v1/shortcut/node
    HEADER: X-Beam-User: <api_user>
            X-Beam-Key: <api_key>
            Content-Type: application/json
    BODY: {
            "<node_name_1>": {},
            "<node_name_n>": {},
          }

Example:

    import json, requests
    lbproxy_headers = {'X-Beam-User': '<api_user>', 'X-Beam-Key': '<api_key>'}
    lbproxy_body = {'<node1_name>': {}, '<node1_name>': {}}
    lbproxy_request = requests.get('https://<lbproxy_host>/v1/shortcut/node/',
                                    headers=lbproxy_headers,
                                    data=json.dumps(lbproxy_body))
    lbproxy_data = json.loads(lbproxy_request.text)
    print(lbproxy_data)

Expected answer:

    {
        "node_name_1": {
            "/partition/pool1": "enabled", "/partition/pool2": "enabled"
        },
        "node_name_2": {
            "/partition/pool1": "enabled", "/partition/pool2": "enabled"
        }
    }

Endpoint:

    @put /v1/shortcut/node

What does it do:
    Enables or disables nodes LB-wide (in all pools)

What does a request look like:

    PUT /v1/shortcut/node
    HEADER: X-Beam-User: <api_user>
            X-Beam-Key: <api_key>
            Content-Type: application/json
    BODY: {
            "<node_name_1>": { "status": "<enabled|disabled>" },
            "<node_name_2>": { "status": "<enabled|disabled>" },
            ...
          }

Example:

    import json, requests
    lbproxy_headers = {'X-Beam-User': '<api_user>', 'X-Beam-Key': '<api_key>'}
    lbproxy_body = {'node_name_1': {'status': 'enabled'},
                    'node_name_2': {'status': 'enabled'}}
    lbproxy_request = requests.get('https://<lbproxy_host>/v1/shortcut/node/',
                                    headers=lbproxy_headers,
                                    data=json.dumps(lbproxy_body))
    lbproxy_data = json.loads(lbproxy_request.text)
    print(lbproxy_data)

Expected answer:

    {
        'node_name_1': 'enabled',
        'node_name_2': 'enabled'
    }


### Other shortcuts

Endpoint:

    @get /v1/shortcut/pool/<partition>/<pool>

Answer:

    {
        "disabled": [],
        "enabled": ["node_name_1", "node_name_2"],
    }

    @put /v1/shortcut/pool/<partition>/<pool>

Payload:

    {
        "disabled": ["node_name_1"],
    }

Answer:
    {
        "disabled": ["node_name_1"],
        "enabled": ["node_name_2"],
    }

Endpoint:

    @get /v1/shortcut/partition/WWW

Answer:

    {
        "/WWW/pool_1": {"disabled": [], "enabled": ["node_name_1"]},
        "/WWW/pool_2": {"disabled": [], "enabled": ["node_name_2"]},
    }

    @put /v1/shortcut/partition/WWW

Payload:

    {
        "disabled": ["node_name_1"]
    }

Answer:

    {
        "/WWW/pool_1": {"disabled": [], "enabled": ["node_name_1"]},
        "/WWW/pool_2": {"disabled": ["node_name_2"], "enabled": ["node_name_3"]},
    }

### Standard API endpoints

These are meant to be used by sysadmins, right now they go straight to the
loadbalancer to query it, which makes it somewhat slow. This also means you
need to know the load balancer on which the objects you are querying are set
up on

Endpoint:

    @get /v1/<loadbalancer/node/<node>

What does it do:
    Returns node configuration information

What does a request look like:

    GET /v1/<loadbalancer>/node/<node>
    HEADER: X-Beam-User: <api_user>
            X-Beam-Key: <api_key>

Example:

    curl -H 'X-Beam-User: <api_user>' -H 'X-Beam-Key: <api_key>' -i -X GET 'https://<lbproxy_host>/v1/<loadbalancer>/node/node_name_1'


Endpoint:

    @get /v1/<loadbalancer>/pool/<partition>/<pool>

What does it do:
    Returns pool configuration information or the
    configuration of specific pool members or all of them

What does a request look like:

    GET /v1/<loadbalancer>/pool/<partition>/<pool>
    or
    GET /v1/<loadbalancer>/pool/<partition>/<pool>?member=<pool_member_name|all>
    HEADER: X-Beam-User: <api_user>
            X-Beam-Key: <api_key>

Example:

    curl -H 'X-Beam-User: <api_user>' -H 'X-Beam-Key: <api_key>' -i -X GET 'https://<lbproxy_host>/v1/<load_balancer>/pool/<partition>/<pool>'
    curl -H 'X-Beam-User: <api_user>' -H 'X-Beam-Key: <api_key>' -i -X GET 'https://<lbproxy_host>/v1/<load_balancer>/pool/<partition>/<pool>?member=all' -- returns information about all pool members
    curl -H 'X-Beam-User: <api_user>' -H 'X-Beam-Key: <api_key>' -i -X GET 'https://<lbproxy_host>/v1/<load_balancer>/pool/<partition>/<pool>?member=<node_name>' -- returns information about 'node_name'


Endpoint:

    @get /v1/<loadbalancer/virtualserver/<partition>/<virtualserver>

What does it do:
    Returns virtualserver configuration information

What does a request look like:

    GET /v1/<loadbalancer>/virtualserver/<virtualserver>
    HEADER: X-Beam-User: <api_user>
            X-Beam-Key: <api_key>

Example:

    curl -H 'X-Beam-User: <api_user>' -H 'X-Beam-Key: <api_key>' -i -X GET 'https://<lbproxy_host>/v1/<loadbalancer>/virtualserver/<partition>/<pool>'

Endpoint:

    @post /v1/<loadbalancer/node

What does it do:
    Add a new node to the loadbalancer

What does a request look like:

    POST /v1/<loadbalancer>/node
    HEADER: X-Beam-User: <api_user>
            X-Beam-Key: <api_key>
            Content-Type: application/json
    BODY: { "<node_name>":
            {
                "address": "<ip_address>",
                "connection_limit": "<conn_limit>"
            }
          }

Example:

    curl -H 'X-Beam-User: <api_user>' -H 'X-Beam-Key: <api_key>' -H 'Content-Type: application/json' -i -X POST -d '{"test": {"address": "1.2.3.4", "connection_limit": "0"}}' 'https://<lbproxy_host>/v1/<loadbalancer>/node'


Endpoint:

    @post /v1/<loadbalancer>/pool/<partition>

What does it do:
    Add a new pool to the loadbalancer and
    members to it

What does a request look like:

    POST /v1/<loadbalancer>/pool/<partition>
    HEADER: X-Beam-User: <api_user>
            X-Beam-Key: <api_key>
            Content-Type: application/json
    BODY: { "<pool_name>":
              {
                "lbmethod": "<lbmethod>",
                "members":
                    {
                        "<poolmember_name>": { "port": "<port>", "ratio": "<ratio>" },
                        ...
                        "<poolmember_name>": { "port": "<port>", "ratio": "<ratio>" },
                    }
              }
           }

Example:

    curl -H 'X-Beam-User: <api_user>' -H 'X-Beam-Key: <api_key>' -H 'Content-Type: application/json' -i -X POST -d '{"test": {"lbmethod": "ratio_member", "members": {"test": {"port": "80", "ratio": "5"}}}}' 'https://<lbproxy_host>/v1/<load_balancer>/pool/<partition>' -- the 'lbmethod' can be 'round_robin' or 'ratio_member'. You can also not use the 'members' attribute and it will just add an empty pool


Endpoint:

    @post /v1/<loadbalancer>/virtualserver/<partition>

What does it do:
    Add a new virtualserver to the loadbalancer

What does a request look like:

    POST /v1/<loadbalancer>/virtualserver/<partition>
    HEADER: X-Beam-User: <api_user>
            X-Beam-Key: <api_key>
            Content-Type: application/json
    BODY: { "<virtualserver_name>":
            {
                "address": "<ip_address>",
                "port": "<listen_port>",
                "pool": "<default_pool_name>",
                "protocol": "<protocol>"
            }
          }

Example:

    curl -H 'X-Beam-User: <api_user>' -H 'X-Beam-Key: <api_key>' -H 'Content-Type: application/json' -i -X POST -d '{"test": {"address": "5.5.5.5", "port": "80", "pool": "test", "protocol": "tcp"}}' 'https://<lbproxy_host>/v1/<loadbalancer>/virtualserver/<partition>'


Endpoint:

    @put /v1/<loadbalancer>/node

What does it do:
    Modify a node's properties on the
    loadbalancer level

What does a request look like:

    PUT /v1/<loadbalancer>/node
    HEADER: X-Beam-User: <api_user>
            X-Beam-Key: <api_key>
            Content-Type: application/json
    BODY: { "<node_name>":
             {
                "ratio": "<ratio>",
                "connection_limit": "<conn_limit>"
                "enabled": "<true|false>"
             }
          }

Example:

    curl -H 'X-Beam-User: <api_user>' -H 'X-Beam-Key: <api_key>' -H 'Content-Type: application/json' -i -X PUT -d '{"test": {"ratio": "2", "connection_limit": "5"}}' 'https://<lbproxy_host>/v1/<loadbalancer>/node'
    curl -H 'X-Beam-User: <api_user>' -H 'X-Beam-Key: <api_key>' -H 'Content-Type: application/json' -i -X PUT -d '{"test": {"enabled": "false"}}' 'https://<lbproxy_host>/v1/<loadbalancer>/node' -- this disables the node 'test' lb-wide, so in all pools


Endpoint:

    @put /v1/<loadbalancer>/pool/<partition>

What does it do:
    Modify a pool's properties or membership
    or members' properties

What does a request look like:

    PUT /v1/<loadbalancer>/pool/<partition>
    HEADER: X-Beam-User: <api_user>
            X-Beam-Key: <api_key>
            Content-Type: application/json
    BODY: { "<pool_name>":
            {
                "lbmethod": "<lbmethod>",
                "description": "<description>",
            }
          }
    OR
    BODY: { "<pool_name>":
            {
                "members":
                    {
                        "<poolmember_name>": {
                            "port": "<port>",
                            "ratio": "<ratio>",
                            "description": "<description>",
                            "enabled": "<true|false>" },
                    }
                    ...<repeat>...
            }
          }

Example:

    curl -H 'X-Beam-User: <api_user>' -H 'X-Beam-Key: <api_key>' -H 'Content-Type: application/json' -i -X PUT -d '{"test": {"lbmethod": "round_robin"}}' 'https://<lbproxy_host>/v1/<loadbalancer>/pool/<partition>'
    curl -H 'X-Beam-User: <api_user>' -H 'X-Beam-Key: <api_key>' -H 'Content-Type: application/json' -i -X PUT -d '{"test": {"members": {"node_name_1": {"port": "80", "ratio": "5"}}}}' 'https://<lbproxy_host>/v1/<loadbalancer>/pool/<partition>' -- this just modifies the node '<node_name_1>' ratio. You always have to specifiy its port as it is part of its identification
    curl -H 'X-Beam-User: <api_user>' -H 'X-Beam-Key: <api_key>' -H 'Content-Type: application/json' -i -X PUT -d '{"test": {"members": {"test": {"port": "80", "enabled": "false"}}}}' 'https://<lbproxy_host>/v1/<loadbalancer>/pool/<partition>' -- this disables the 'test' node just in the 'test' pool. You always have to specifiy its port as it is part of its identification


Endpoint:

    @put /v1/<loadbalancer>/virtualserver/<partition>

What does it do:
    Modify a virtualserver's properties

What does a request look like:

    PUT /v1/<loadbalancer>/virtualserver/<partition>
    HEADER: X-Beam-User: <api_user>
            X-Beam-Key: <api_key>
            Content-Type: application/json
    BODY: { "<virtualserver_name>":
            {
                "address": "<ip_address>",
                "port": "<listen_port>",
                "description": "<description>",
                "pool": "<default_pool_name>",
                "protocol": "<protocol>"
            }
          }

Example:

    curl -H 'X-Beam-User: <api_user>' -H 'X-Beam-Key: <api_key>' -H 'Content-Type: application/json' -i -X PUT -d '{"test": {"port": "443"}}' 'https://<lbproxy_host>/v1/<loadbalancer>/virtualserver/<partition>' -- we just changed the 'test' virtualserver's listen port


Endpoint:

    @delete /v1/<loadbalancer>/node

What does it do:
    Delete a node lb-wide (from all pools)

What does a request look like:

    DELETE /v1/<loadbalancer>/node
    HEADER: X-Beam-User: <api_user>
            X-Beam-Key: <api_key>
            Content-Type: application/json
    BODY: { "<node_name>": {} }

Example:

    curl -H 'X-Beam-User: <api_user>' -H 'X-Beam-Key: <api_key>' -H 'Content-Type: application/json' -i -X DELETE -d '{"test": {}}' 'https://<lbproxy_host>/v1/<loadbalancer>/node' -- we deleted the 'test' node from everywhere on the loadbalancer


Endpoint:

    @delete /v1/<loadbalancer>/pool/<partition>

What does it do:
    Delete a pool or members from that pool

What does a request look like:

    DELETE /v1/<loadbalancer>/pool/<partition>
    HEADER: X-Beam-User: <api_user>
            X-Beam-Key: <api_key>
            Content-Type: application/json
    BODY: { "<pool_name>": {} }
    OR
    BODY: { "<pool_name>":
            {
                "members": { "<poolmember_name>": {} }
                ...repeat...
            }
          }

Example:

    curl -H 'X-Beam-User: <api_user>' -H 'X-Beam-Key: <api_key>' -H 'Content-Type: application/json' -i -X DELETE -d '{"test": {"members": {"test": {}}}}' 'https://<lbproxy_host>/v1/<loadbalancer>/pool/<partition>' -- we just deleted the 'test' node from the 'test' pool
    curl -H 'X-Beam-User: <api_user>' -H 'X-Beam-Key: <api_key>' -H 'Content-Type: application/json' -i -X DELETE -d '{"test": {}}' 'https://<lbproxy_host>/v1/<loadbalancer>/pool/<partition>' -- we deleted the entire 'test' pool


Endpoint:

    @delete /v1/<loadbalancer>/virtualserver/<partition>

What does it do:
    Delete a virtualserver

What does a request look like:

    DELETE /v1/<loadbalancer>/virtualserver/<partition>
    HEADER: X-Beam-User: <api_user>
            X-Beam-Key: <api_key>
            Content-Type: application/json
    BODY: { "<virtualserver_name>": {} }

Example:

    curl -H 'X-Beam-User: <api_user>' -H 'X-Beam-Key: <api_key>' -H 'Content-Type: application/json' -i -X DELETE -d '{"test": {}}' 'https://<lbproxy_host>/v1/<loadbalancer>/virtualserver/<partition>'
