import unittest, os
from fabric.api import env
from cotton.salt import pillar


class TestPillarMethods(unittest.TestCase):

    env.project = 'foo'
    expected_roots = [os.path.dirname(os.path.realpath(__file__))+ '/data']
    env.pillar_roots = expected_roots
    env.real_fabfile = __file__

    def test_get_unrendered_pillar_location(self):
        expected = '/config/projects/{}/pillar'.format(env.project)
        result = pillar.get_unrendered_pillar_location()

        self.assertNotEqual(result.find(expected), -1)

    def test_get_unrendered_pillar_locations_no_project(self):
        self.assertEqual(pillar.get_unrendered_pillar_locations(False), env.pillar_roots)

    def test_get_unrendered_pillar_locations_with_project(self):
        result = pillar.get_unrendered_pillar_location()
        pillar_locations = pillar.get_unrendered_pillar_locations()
        self.assertNotEqual(pillar_locations, env.pillar_roots)
        env.pillar_roots.insert(0, result)
        self.assertEqual(pillar_locations, env.pillar_roots)

    def test_get_projects_location(self):
        location = pillar._get_projects_location()
        expected_location = os.path.abspath(os.path.join(__file__ , '../../config/projects/'))
        self.assertEqual(location, expected_location)

    def test_get_rendered_pillar_location_throws_no_top_sls_exception(self):
        with self.assertRaises(RuntimeError) as context:
           pillar.get_rendered_pillar_location()

        expected_message = 'Missing top.sls in pillar location. Skipping rendering.'
        self.assertEqual(str(context.exception), expected_message)

    def test_get_rendered_pillar_location_renders_pillar(self):
        result = pillar.get_rendered_pillar_location(None, None, False)
        self.assertNotEqual(result.find('/tmp/tmp'), -1)
