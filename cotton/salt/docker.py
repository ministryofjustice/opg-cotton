from fabric.api import sudo


def run_docker_compose_command(
        grain_target='test',
        target_stack='aws-develop',
        docker_compose_args='',
        env_vars='',
        entry_point_args='',
        target_dir=None):

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
