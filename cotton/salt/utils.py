from fabric.api import env
from cotton.colors import yellow
from cotton.api import configure_fabric_for_host
from ast import literal_eval
import os


def build_salt_dirs():
    import yaml
    """
    get list of pillar directories for cotton
    :return: dict with list of dirs or error
    """
    print(yellow("{}".format('Building pillar directory list')))
    try:
        dir_list = []
        not_found = []
        root_list = []
        with open('sources.yml') as f:
            _dirs = yaml.safe_load(f)
        pillar_dirs = _dirs['pillar'][env.provider_zone] + _dirs['pillar']['common']
        pillar_roots = _dirs['pillar_roots'][env.provider_zone] + _dirs['pillar_roots']['common']

        for pillar_dir_name in pillar_dirs:
            if os.path.exists(pillar_dir_name):
                dir_list.append(pillar_dir_name)
            else:
                not_found.append(pillar_dir_name)

        for pillar_root_dir in pillar_roots:
            for root, dirs, files in os.walk(pillar_root_dir):
                rel_path = os.path.relpath(root, dirs)
                if os.path.exists(rel_path):
                    root_list.append(rel_path)
                else:
                    not_found.append(rel_path)

        return {'pillar_dir': dir_list, 'pillar_root': root_list, 'missing': not_found}
    except (OSError,  IOError):
        return {'error': 'Failed to open sources.yml'}


def common_configurations(salt_master=True, pillar_dirs=None, pillar_roots=None):
    """
    Common env configurations
    :param pillar_roots: list of pillar root source directories
    :param new_master: only set to True if master is being rebuilt
    :param salt_master: Master or masterless salt, defaults to True(has a master)
    :param pillar_dirs: a ; separated list of directories to merge based on your top.sls
    :return:
    """
    env.project = 'pillar/{stackname}'.format(stackname=env.stackname)  # that's where pillars are taken from
    env.saltmaster = salt_master
    env.retain_dirs = True

    if env.new_master:
        env.gateway_user = 'jenkins-agent'

    env.private_dns = configure_fabric_for_host(name='master.{}'.format(env.stackname))

    if "gateway" not in env:
        env.gateway = 'jump.{stackname}.{domainname}'.format(stackname=env.stackname, domainname=env.domainname)

    print("Pipeline: {stackname}.{domainname}".format(stackname=env.stackname, domainname=env.domainname))
    salt_dirs = build_salt_dirs()
    if isinstance(salt_dirs, dict):
        if 'error' in salt_dirs:
            print("Error parsing directories:\n{}".format(salt_dirs['error']))
        else:
            if pillar_dirs is None:
                env.pillar_dirs = salt_dirs['pillar_dir']

            if pillar_roots is None:
                env.pillar_roots = salt_dirs['pillar_root']

            if len(salt_dirs['missing']) > 0:
                print("Missing directories: \n{}".format(salt_dirs['missing']))


def configure_master_host(new_master=False):
    """
    Configures our master
    :param new_master:
    :return:
    """
    if new_master:
        env.new_master = literal_eval(new_master)
    else:
        env.new_master = new_master
    if env.target_host == 'localhost':
        env.vm_name = '127.0.0.1'
    else:
        common_configurations()
