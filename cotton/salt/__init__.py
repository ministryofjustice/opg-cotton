"""
root/
|-- application-deployment/
|   `-- fabfile.py
`-- config/projects/{project}/pillar/
"""

from cotton.salt.pillar import *  # noqa
from cotton.salt.shaker import *  # noqa
from cotton.salt.wrappers import *  # noqa
from cotton.salt.tasks import *  # noqa
