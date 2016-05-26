import unittest
import os
from fabric.api import env
from cotton.salt import tasks

class TestTaskMethods(unittest.TestCase):
    env.project = 'foo'
    expected_roots = [os.path.dirname(os.path.realpath(__file__)) + '/data']
    env.pillar_roots = expected_roots
    env.real_fabfile = __file__

    def mocked_rsync(self):
        return 'Rsync_happened'

    @unittest.expectedFailure
    def test_rsync(self):
        from cotton import api
        tasks.__rsync_salt = self.mocked_rsync()
        tasks.__rsync_pillars = self.mocked_rsync()
        tasks.__rsync_salt_formulas = self.mocked_rsync()
        api.vm_task = self.mocked_rsync()

        tasks.rsync()


