from ansibleutils import AnsibleUtilities
from fabric.api import task


@task
def run_ansible_playbook(
        playbook_name=None,
        playbooks_version='master',
        playbook_path='opg-playbooks',
        roles_version='master',
        destroy_stack=False,
        debug=False
):
    """
    :param playbook_name:
    :param playbook_path:
    :param roles_version:
    :param destroy_stack:
    :param debug: verbosity of playbook output
    :return:
    """
    AnsibleUtilities.run_ansible_playbook(
        roles_version=roles_version,
        destroy_stack=destroy_stack,
        playbook_name=playbook_name,
        playbook_path=playbook_path,
        playbooks_version=playbooks_version,
        debug=debug
    )

