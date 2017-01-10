# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
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

import configparser

from lbproxy.utils import get_logger

logger = get_logger()


class Auth(object):
    def do(self, request):
        try:
            config = configparser.ConfigParser()
            config_file = '/etc/lbproxy/auth.cfg'
            config.read(config_file)
            username = request.headers.get('X-Beam-User')
            key = request.headers.get('X-Beam-Key')
            if username == None or key == None:
                logger.info('Missing X-Beam-User or X-Beam-Key headers')
                return False

            logger.error('Authenticating user %s' % username)
            if config.get('lbproxy', username) == key:
                return True
            else:
                return False
        except Exception as e:
            logger.error('Problem authenticating: %s' % e.__str__())
