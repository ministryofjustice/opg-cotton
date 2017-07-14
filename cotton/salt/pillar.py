import os
import tempfile
import yaml

from fabric.api import env

from cotton.colors import red, green, yellow


def get_unrendered_pillar_location():
    """
    returns local pillar location
    """
    if env.use_project_dir:
        # TODO: render pillar template to stdout / temp directory to sync it? (or just generate one file for remote)
        fab_location = os.path.dirname(env.real_fabfile)
        pillar_location = os.path.abspath(os.path.join(fab_location, '../config/projects/{}/pillar'.format(env.project)))

    return pillar_location


def get_unrendered_pillar_locations(include_project=True):
    """
    Returns all local pillar locations
    If a boolean false is passed as an argument it will not include the project pillar
    """

    pillar_locations = []

    if include_project:
        pillar_locations.append(get_unrendered_pillar_location())

    if 'pillar_dirs' in env:
        fab_location = os.path.dirname(env.real_fabfile)
        for root in env.pillar_dirs:
            pillar_locations.append(os.path.abspath(os.path.join(fab_location, root)))

    return pillar_locations


def _get_projects_location():
    if env.use_project_dir:
        fab_location = os.path.dirname(env.real_fabfile)
        return os.path.abspath(os.path.join(fab_location, '../config/projects/'))


def get_rendered_pillar_location(
        pillar_dir=None,
        projects_location=None,
        parse_top_sls=True,
        target=None
    ):
    """
    Returns path to rendered pillar.
    Use to render pillars written in jinja locally not to upload unwanted data to network.

    i.e. you can use constructs like:
    {% include 'opg-lpa-dev/pillar/services.sls' %}

    If you want salt to later render pillars with grain context use constructs like:
    {% raw %} {{grains.get('roles')}} {% endraw %}
    {{" {{grains.get('roles')}} "}}

    To allow for server side templating of top.sls, you will need set: `parse_top_sls=False`

    In case there is no top.sls in pillar root than it returns: None
    """
    if 'use_project_dir' not in 'env':
        env.use_project_dir = False

    if projects_location is None:
        projects_location = _get_projects_location()

    pillars = __load_pillar_dirs(pillar_dir, projects_location, target)
    jinja_env = _set_template_env(pillars, projects_location)

    dest_location = tempfile.mkdtemp()

    if parse_top_sls:
        files_to_render = _pillar_from_top_sls(dest_location, jinja_env)
    elif len(pillars):
        files_to_render, output_dir = _pillar_from_dirs(pillars)
    else:
        print(yellow("No template files where found to render"))
        files_to_render = []

    if __render_templates(files_to_render, dest_location, jinja_env) is False:
        print(red("Aborting due to pillar failing to render"))
        exit(-1)

    return dest_location


def _pillar_from_dirs(pillars):
    files_to_render = []
    output_dir = None
    # let's select all files from pillar directory

    for pillar in pillars:
        for root, dirs, files in os.walk(pillar):
            rel_path = os.path.relpath(root, pillar)
            for file_name in files:
                # if 'retain_dirs' in env and env.retain_dirs:
                if 'retain_dirs' in env and env.retain_dirs:
                    output_dir = root.replace('./pillar', '.') if 'pillar' in root else rel_path
                    files_to_render.append(os.path.join(output_dir, file_name))
                else:
                    files_to_render.append(os.path.join(rel_path, file_name))
    return files_to_render, output_dir


def _pillar_from_top_sls(dest_location, jinja_env):
    from jinja2.exceptions import TemplateNotFound

    files_to_render = []

    # let's parse top.sls to only select files being referred in top.sls
    try:
        top_sls = jinja_env.get_template('top.sls').render(env=env)
    except TemplateNotFound:
        raise RuntimeError("Missing top.sls in pillar location. Skipping rendering.")
    top_content = yaml.load(top_sls)
    filename = os.path.join(dest_location, 'top.sls')
    with open(filename, 'w') as f:
        print("Pillar template_file: {} --> {}".format('top.sls', filename))
        f.write(top_sls)
    for k0, v0 in top_content.iteritems():
        for k1, v1 in v0.iteritems():
            for file_short in v1:
                # We force this file to be relative in case jinja failed rendering
                # a variable. This would make the filename start with / and instead of
                # writing under dest_location it will try to write in /
                if isinstance(file_short, str):
                    files_to_render.append('./' + file_short.replace('.', '/') + '.sls')

    return files_to_render


def _set_template_env(pillars, projects_location):
    from jinja2 import Environment
    from jinja2 import FileSystemLoader

    # We need to merge our directory trees here so that we don't mess with the pillars list
    # if so we may try to connect to something that doesn't actually exist
    relative_pillars = []
    for pillar in pillars:
        if 'pillar/' in pillar:
            pillar = 'pillar/'
        relative_pillars.append(pillar)

    template_dirs = list(relative_pillars)
    template_dirs.append(projects_location)
    # String out None or anything empty
    template_dirs = filter(None, template_dirs)
    if len(template_dirs):
        jinja_env = Environment(loader=FileSystemLoader(template_dirs))
    else:
        raise RuntimeError("No source template directories are specified, aborting")
    return jinja_env


def __load_pillar_dirs(pillar_dir, projects_location, target=None):
    """
    Loads all of the pillar directories into a list
    :param pillar_dir: string
    :param projects_location: string
    :return pillars: list
    """
    pillars = []

    # We can bypass the project directory when creating the pillar
    if pillar_dir is None and env.use_project_dir is True:
        if "pillar_dir" in env:
            pillar_dir = env.pillar_dir
        else:
            assert env.project, "env.project or env.pillar_dir must be specified"
            pillar_dir = os.path.join(projects_location, env.project, 'pillar')

        pillars.append(pillar_dir)

    if 'pillar_dirs' in env and env.pillar_dirs:
        for root in env.pillar_dirs:
            pillars.append(root)

    pillars = list(set(pillars))

    if target:
        return list(filter(lambda x: target in x, pillars))

    return pillars


def __render_templates(files_to_render, dest_location, jinja_env):

    """
    Render and save templates
    """
    errors = []

    from jinja2.exceptions import TemplateNotFound

    for template_file in files_to_render:
        filename = os.path.abspath(os.path.join(dest_location, template_file))

        print("Pillar template_file: {} --> {}".format(template_file, filename))

        if not os.path.isdir(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))

        try:
            print("Attempting to load template_file: {}".format(template_file))
            template_rendered = jinja_env.get_template(template_file).render(env=env)
            print(green("Pillar template_file rendered: {} --> {}".format(template_file, filename)))

            # Only write the template file if we can actually render it
            with open(os.path.join(dest_location, template_file), 'w') as f:
                f.write(template_rendered)

        except TemplateNotFound:
            errors.append(template_file)
            print(red("Pillar template_file not found: {} --> {}".format(template_file, filename)))

    if not len(errors):
        print(green("Pillar was successfully rendered in: {}".format(dest_location)))
    else:
        print(red("Pillar could not compile the following templates:"))
        for error in errors:
            print(red(" - {}").format(error))

    return len(errors) == 0

get_pillar_location = get_rendered_pillar_location
get_pillar_dirs = __load_pillar_dirs
