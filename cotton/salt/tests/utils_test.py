import unittest
from cotton.salt.utils import build_salt_dirs


class TestUtilsMethods(unittest.TestCase):

    def test_build_salt_dirs_throws_exception(self):
        import sys
        from StringIO import StringIO
        stdout = sys.stdout

        try:
            new_stdout = StringIO()
            sys.stdout = new_stdout

            result = build_salt_dirs()
            output = new_stdout.getvalue().strip()
            self.assertIn('Building pillar directory list', output)
            self.assertEqual(result, {'error': 'Failed to open sources.yml'})
            self.assertRaises(IOError)
        finally:
            sys.stdout = stdout

    def test_build_salt_dirs_with_generated_file(self):
        import sys
        from StringIO import StringIO
        from fabric.api import env
        env.provider_zone = 'foo'
        stdout = sys.stdout
        self.create_test_yaml_file()

        try:
            new_stdout = StringIO()
            sys.stdout = new_stdout

            result = build_salt_dirs()
            output = new_stdout.getvalue().strip()

            self.assertIn('Building pillar directory list', output)
            self.assertEqual(result,
                {
                    'missing': ['./foo', './common', './foo', './pillar_roots/common', './pillar_roots/develop'],
                    'pillar_dir': [],
                    'pillar_root': []
                }
            )
        finally:
            sys.stdout = stdout
            self.remove_test_yaml_file()

    @staticmethod
    def remove_test_yaml_file():
        import os
        os.unlink('sources.yml')

    @staticmethod
    def create_test_yaml_file():
        import yaml

        data = dict(
            pillar=dict(
                common=['./common'],
                foo=['./foo']

            ),
             pillar_roots=dict(
                 common=['./pillar_roots/common', './pillar_roots/develop'],
                 foo=['./foo']
             )
        )

        with open('sources.yml', 'w') as outfile:
            yaml.dump(data, outfile, default_flow_style=False)