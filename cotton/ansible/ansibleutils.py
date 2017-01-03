from fabric.api import local, env, lcd
from ast import literal_eval


class AnsibleUtilities(object):

    @staticmethod
    def run_ansible_playbook(roles_version='master', destroy_stack=False):
        """
        Runs an ansible playbook
        :param roles_version:
        :param destroy_stack:
        :return:
        """
        # add extra vars to this string
        extra_vars = 'target={} opg_ansible_version={}'.format(env.stackname, roles_version)
        if isinstance(destroy_stack, basestring):
            destroy_stack = literal_eval("{}".format(destroy_stack).lower().capitalize())
        if destroy_stack:
            extra_vars = '{} {}'.format(extra_vars, 'destroy_stack=true')
        with lcd('ansible'):
            # checkout roles from opg-ansible-roles repo
            local('ansible-playbook -i hosts site.yml -e "' + extra_vars + '"')
            # run provisioning playbook
            local('ansible-playbook -i hosts provision.yml -e "' + extra_vars + '" -v')
