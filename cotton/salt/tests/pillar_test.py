import unittest, os
from fabric.api import env
from cotton.salt import pillar


class TestPillarMethods(unittest.TestCase):

    env.project = 'foo'
    expected_roots = [os.path.dirname(os.path.realpath(__file__)) + '/data']
    env.pillar_dirs = expected_roots
    env.real_fabfile = __file__

    def test_get_unrendered_pillar_location(self):
        env.use_project_dir = True
        expected = '/config/projects/{}/pillar'.format(env.project)
        result = pillar.get_unrendered_pillar_location()

        self.assertNotEqual(result.find(expected), -1)

    def test_get_unrendered_pillar_locations_no_project(self):
        env.use_project_dir = False
        self.assertEqual(pillar.get_unrendered_pillar_locations(False), env.pillar_dirs)

    def test_get_unrendered_pillar_locations_with_project(self):
        env.use_project_dir = True
        result = pillar.get_unrendered_pillar_location()
        pillar_locations = pillar.get_unrendered_pillar_locations()
        self.assertNotEqual(pillar_locations, env.pillar_dirs)
        env.pillar_dirs.insert(0, result)
        self.assertEqual(pillar_locations, env.pillar_dirs)

    def test_get_projects_location(self):
        env.use_project_dir = True
        location = pillar._get_projects_location()
        expected_location = os.path.abspath(os.path.join(__file__ , '../../config/projects/'))
        self.assertEqual(location, expected_location)

    def test_get_rendered_pillar_location_no_pillar_dirs_throws_exception(self):
        env.use_project_dir = False
        expected_roots = env.pillar_dirs
        env.pillar_dirs = None
        with self.assertRaises(RuntimeError) as context:
            pillar.get_rendered_pillar_location()

        expected_message = 'No source template directories are specified, aborting'
        self.assertEqual(str(context.exception), expected_message)
        env.pillar_dirs = expected_roots

    def test_get_rendered_pillar_location_no_top_sls_exception(self):
        env.use_project_dir = True
        with self.assertRaises(RuntimeError) as context:
            pillar.get_rendered_pillar_location()

        expected_message = 'Missing top.sls in pillar location. Skipping rendering.'
        self.assertEqual(str(context.exception), expected_message)

    # def test_get_rendered_pillar_location_renders_pillar(self):
    #     env.use_project_dir = True
    #     result = pillar.get_rendered_pillar_location(parse_top_sls=False)
    #     self.assertNotEqual(result.find('/tmp/tmp'), -1)

    def test_get_rendered_pillar_location_with_no_config_dirs(self):
        env.use_project_dir = False
        pillar_dirs = env.pillar_dirs
        env.pillar_dirs = None

        with self.assertRaises(RuntimeError) as context:
            pillar.get_rendered_pillar_location(parse_top_sls=False)

        expected_message = 'No source template directories are specified, aborting'
        self.assertEqual(str(context.exception), expected_message)

        env.use_project_dir = True
        env.pillar_dirs = pillar_dirs

