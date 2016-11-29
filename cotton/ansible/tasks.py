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
        lifetime_days=5,
        target_branch='master'
):
    """
    Create and commit an new ansible based stack for feature branch development and testing
    :param target_stackname:
    :param sources_section:
    :param source_stackname:
    :param lifetime_days:
    :param target_branch:
    """
    feature_branch = FeatureBranch()
    feature_branch.create_feature_stack(
        target_stackname=target_stackname,
        source_stackname=source_stackname,
        lifetime_days=lifetime_days,
        sources_section=sources_section
    )

    feature_branch.commit_feature_stack(target_branch=target_branch)


@task
def delete_feature_stack(
        target_stackname,
        sources_section,
        target_branch='master'
):
    """
    Remove and commit an unneeded created feature stack
    :param target_stackname:
    :param sources_section:
    :param target_branch:
    :return:
    """
    feature_branch = FeatureBranch()
    feature_branch.remove_feature_stack(
        target_stackname=target_stackname,
        sources_section=sources_section
    )

    feature_branch.commit_feature_stack(target_branch=target_branch)
