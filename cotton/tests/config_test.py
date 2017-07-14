import unittest, os
from fabric.api import env
from cotton import config


class TestConfigMethods(unittest.TestCase):

    def test_no_env_files_gives_me_default_location(self):
        env.project = None
        env.pillar_dirs = None
        result = config._generate_config_path_and_dirs(os.path.dirname("/tmp"))
        self.assertNotEqual(len(result[1]), 0)
        self.assertEqual(result[1], "{}/projects".format(os.path.dirname("/tmp")))

    def test_config_location_in_env_gives_me_project_location(self):
        env.use_project_dir = True
        proj_dir = env.project
        env.project = None
        result = config._generate_config_path_and_dirs(os.path.dirname("/tmp"))
        self.assertGreater(len(result[1]), 0)
        self.assertEqual(result[1], "//projects")
        env.project = proj_dir

    def test_project_location_in_env_gives_me_a_location(self):
        env.use_project_dir = True
        proj_dir = env.project
        env.project = os.path.dirname(os.path.realpath(__file__))
        result = config._generate_config_path_and_dirs(os.path.dirname(os.path.realpath(__file__)), [])
        self.assertGreater(len(result[1]), 0)
        self.assertEqual(result[1], "{}/projects/{}".format(env.project, env.project))
        self.assertEqual(len(result[0]), 0)
        env.project = proj_dir

    def test_pillar_dirs_go_to_config_dirs(self):
        env.use_project_dir = False
        expected  = ["/tmp", os.path.dirname(os.path.realpath(__file__))]
        env.pillar_dirs = expected
        result = config._generate_config_path_and_dirs(os.path.dirname(os.path.realpath(__file__)))
        self.assertEqual(len(result[0]), 2)
        self.assertEqual(result[0], expected)

    def test_deep_merge(self):
        dict_a = {'foo':'bar'}
        dict_b = {'bar':'baz'}
        expected = {'foo':'bar', 'bar':'baz'}

        self.assertEqual(expected, config.dict_deepmerge(dict_b, dict_a))
