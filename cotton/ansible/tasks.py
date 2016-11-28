from ansibleutils import AnsibleUtilities
from featurebranch import FeatureBranch
from fabric.api import task
from cotton.colors import red


@task
def run_ansible_playbook(
        playbook_name=None,
        playbooks_version='master',
        playbook_path='opg-playbooks',
        roles_version='master',
        destroy_stack=False
):
    """
    :param playbook_name:
    :param playbook_path:
    :param roles_version:
    :param destroy_stack:
    :return:
    """
    AnsibleUtilities.run_ansible_playbook(
        roles_version=roles_version,
        destroy_stack=destroy_stack,
        playbook_name=playbook_name,
        playbook_path=playbook_path,
        playbooks_version=playbooks_version
    )


@task
def create_feature_stack(
        target_stackname,
        sources_section,
        source_stackname='aws-develop',
        lifetime_days=5
):
    feature_branch = FeatureBranch()
    # try:
    feature_branch.create_feature_stack(
        target_stackname=target_stackname,
        source_stackname=source_stackname,
        lifetime_days=lifetime_days,
        sources_section=sources_section
    )

    feature_branch.commit_feature_stack(target_stackname)
    # except :
    #     print(red('Failed to create {} aborting'.format(target_stackname)))
