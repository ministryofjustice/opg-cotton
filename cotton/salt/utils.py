from fabric.api import env, lcd, local
from cotton.colors import yellow
import yaml
import os


def build_salt_dirs():
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

        for pillar_rootdir_name in pillar_roots:
            if os.path.exists(pillar_rootdir_name):
                root_list.append(pillar_rootdir_name)
            else:
                not_found.append(pillar_rootdir_name)

        return {'pillar_dir': dir_list, 'pillar_root': root_list, 'missing': not_found}
    except (OSError,  IOError):
        return {'error': 'Failed to open sources.yml'}




def run_ansible_playbook():
    """
    Run site.yml playbook to checkout provision infrastructure.
    :return:
    """
    if len(env.get('playbook_version', '')) < 1:
        env.playbook_version = 'master'
    # add extra vars to this string
    extra_vars = 'target={} opg_ansible_version={}'.format(env.stackname, env.playbook_version)

    with lcd('ansible'):
        # run provisioning playbook
        local('ansible-playbook -i hosts site.yml -e "' + extra_vars + '"')