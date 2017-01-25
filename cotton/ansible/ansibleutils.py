from fabric.api import local, env, lcd
from ast import literal_eval


class AnsibleUtilities(object):

    @staticmethod
    def run_ansible_playbook(
            playbook_path,
            playbook_name,
            roles_version='master',
            playbooks_version='master',
            destroy_stack=False
    ):
        """
        Runs an ansible playbook
        :param roles_version:
        :param destroy_stack:
        :param playbooks_version:
        :param playbook_name:
        :param playbook_path:
        :return:
        """
        # add extra vars to this string
        extra_vars = 'target={} opg_ansible_version={} opg_playbooks_version={}'.format(env.stackname, roles_version, playbooks_version)
        if isinstance(destroy_stack, basestring):
            destroy_stack = literal_eval("{}".format(destroy_stack).lower().capitalize())
        if destroy_stack:
            extra_vars = '{} {}'.format(extra_vars, 'destroy_stack=true')
        with lcd('ansible'):
            # checkout roles from opg-ansible-roles repo
            local('ansible-playbook -i hosts site.yml -e "' + extra_vars + '"')
            # run provisioning playbook
            playbook_cmd = 'ansible-playbook -i hosts {}/{}.yml -e "{}" -v'.format(playbook_path, playbook_name, extra_vars)
            local(playbook_cmd)
