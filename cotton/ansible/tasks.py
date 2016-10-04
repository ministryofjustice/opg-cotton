from ansibleutils import AnsibleUtilities
from fabric.api import task


@task
def run_ansible_playbook(roles_version='master', destroy_stack=False):
    AnsibleUtilities.run_ansible_playbook(
        roles_version=roles_version,
        destroy_stack=destroy_stack
    )

