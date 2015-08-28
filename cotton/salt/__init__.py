"""
root/
|-- application-deployment/
|   `-- fabfile.py
`-- config/projects/{project}/pillar/
"""

from cotton.salt.pillar import *
from cotton.salt.shaker import *
from cotton.salt.wrappers import *
from cotton.salt.tasks import *
