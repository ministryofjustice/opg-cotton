from fabric.api import sudo


def run_docker_compose_command(
        grain_target='test',
        target_stack='aws-develop',
        docker_compose_args='',
        env_vars='',
        entry_point_args='',
        target_dir=None):
    """
    Runs an ad-hoc docker composer command on a targeted container
    :param grain_target: the target node in the infra
    :param target_stack: the stackname
    :param docker_compose_args:
    :param env_vars:
    :param entry_point_args:
    :param target_dir: the subdir in the docker-compose path
    :return:
    """
    if target_dir is None:
        target_dir = grain_target

    sudo(
        "salt --subset=1 "
        "-C 'G@opg_role:{} and G@opg_stackname:{}' "
        "cmd.run 'cd /etc/docker-compose/{} && docker-compose run {} {} {} {}' -t 60"
        .format(grain_target,
                target_stack,
                target_dir,
                entry_point_args,
                env_vars,
                grain_target,
                docker_compose_args
                )
    )
