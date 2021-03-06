# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import os
import re

from flask import current_app

from repository import Repository
from repository import MercurialException
from repository import UnknownRevisionException

import rest

DEFAULT_WORKDIR = '/var/lib/transplant'
DEFAULT_REPOSITORIES = []

PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))
TRANSPLANT_FILTER = os.path.join(PROJECT_DIR, 'transplant_filter.py')
MAX_COMMITS = 100

Repository.register_extension(
    'collapse',
    os.path.join(PROJECT_DIR, 'vendor', 'hgext', 'collapse.py')
)

logger = logging.getLogger(__name__)


def is_allowed_transplant(src, dst):
    return src != dst


def find_repo(name):
    repositories = current_app.config.get('TRANSPLANT_REPOSITORIES', DEFAULT_REPOSITORIES)
    for repository in repositories:
        if repository['name'] == name:
            return repository

    return None


def has_repo(name):
    repository = find_repo(name)
    if repository is None:
        return False

    return True


def get_repo_url(name):
    repository = find_repo(name)
    if repository is None:
        raise TransplantError('unknown repository: {}'.format(name))

    return repository['path']


def get_repo_base_url(name):
    repository = find_repo(name)
    if repository is None:
        raise TransplantError('unknown repository: {}'.format(name))

    if 'base' in repository:
        return repository['base']
    else:
        return repository['path']


def get_repo_dir(name):
    workdir = current_app.config.get('TRANSPLANT_WORKDIR', DEFAULT_WORKDIR)
    # make sure that workdir exists
    if not os.path.exists(workdir):
        os.makedirs(workdir)

    return os.path.abspath(os.path.join(workdir, name))


def clone(name, force_update=False):
    repo_url = get_repo_url(name)
    repo_dir = get_repo_dir(name)
    repo_base_url = get_repo_base_url(name)

    if not os.path.exists(os.path.join(repo_dir, '.hg')):
        logger.info('cloning repository "%s"', name)
        repository = Repository.clone(repo_base_url, repo_dir)
    else:
        logger.info('repository "%s" is already cloned', name)
        repository = Repository(repo_dir)
        if force_update:
            logger.info('pulling / updating repository "%s"', name)
            repository.pull(update=True)

    repository.set_config({
        "paths": {
            "default": repo_url,
            "base": repo_base_url
        }
    })

    return repository


def get_revset_info(repository_id, revset):
    repository = clone(repository_id)
    commits = optimistic_log(repository, revset)
    commits_count = len(commits)
    if commits_count > MAX_COMMITS:
        msg = too_many_commits_error(commits_count, MAX_COMMITS)
        raise TooManyCommitsError(msg)

    return rest.RevsetInfo(commits=commits)


def optimistic_log(repository, revset):
    try:
        commits = repository.log(rev=revset)
    except UnknownRevisionException:
        # FIXME: the only supported syntax is "rev1 + rev2 + rev3"
        rev = re.split('\s*\+\s*', revset)

        logger.info('revset "%s" not found in local repository, pulling "%s"',
                    rev, repository.path)
        repository.pull(rev=rev, update=True)
        commits = repository.log(rev=revset)

    return commits


def cleanup(repo):
    logger.info('cleaning up')
    repo.update(clean=True)
    repo.purge(abort_on_err=True, all=True)

    try:
        repo.strip('outgoing(default)', no_backup=True)
    except MercurialException, e:
        if 'empty revision set' not in e.stderr:
            raise e


def raw_transplant(repository, source, revset, message=None):
    filter = None
    env = os.environ.copy()

    if message is not None:
        filter = TRANSPLANT_FILTER
        env['TRANSPLANT_MESSAGE'] = message

    return repository.transplant(revset, source=source, filter=filter, env=env)


def transplant(src, dst, items):
    dst_repo = clone(dst, force_update=True)

    try:
        for item in items:
            transplant_item(src, dst, item)

        logger.info('pushing "%s"', dst)
        dst_repo.push()

        tip = dst_repo.id(id=True)
        logger.info('tip: %s', tip)
        return {'tip': tip}

    finally:
        cleanup(dst_repo)
        pass


def transplant_item(src, dst, item):
    if 'commit' in item:
        transplant_commit(src, dst, item)
    elif 'revset' in item:
        transplant_revset(src, dst, item)
    else:
        raise TransplantError("unknown item: {}".format(item))


def transplant_commit(src, dst, item):
    message = item.get('message', None)
    _transplant(src, dst, item['commit'], message=message)


def transplant_revset(src, dst, item):
    message = item.get('message', None)

    src_repo = clone(src)
    dst_repo = clone(dst)
    commits = optimistic_log(src_repo, item['revset'])
    commits_count = len(commits)
    if commits_count > MAX_COMMITS:
        msg = too_many_commits_error(commits_count, MAX_COMMITS)
        raise TooManyCommitsError(msg)

    if commits_count == 0:
        return

    if commits_count == 1:
        _transplant(src, dst, item['revset'], message=message)
    else:
        old_tip = dst_repo.id(id=True)
        revset = [commit.node for commit in commits]

        # no need to pass message as we'll override it during collapse anyway
        _transplant(src, dst, revset)

        collapse_rev = 'descendants(children({}))'.format(old_tip)
        collapse_commits = dst_repo.log(rev=collapse_rev)

        # less than two commits were transplanted, no need to squash
        if len(collapse_commits) < 2:
            return

        logger.info('collapsing "%s"', collapse_rev)
        last_commit_author = commits[-1].author
        dst_repo.collapse(rev=collapse_rev, message=message, user=last_commit_author)


def _transplant(src, dst, revset, message=None):
    src_repo = clone(src)
    dst_repo = clone(dst)

    # ensure the source revset is pulled from upstream
    optimistic_log(src_repo, revset)

    logger.info('transplanting "%s" from "%s" to "%s"', revset, src, dst)
    result = raw_transplant(dst_repo, src_repo.path, revset, message=message)
    dst_repo.update()

    logger.debug('hg transplant: %s', result)


def too_many_commits_error(current, limit):
    return ("You're trying to transplant {} commits "
            "which is above {} commits limit").format(current, limit)


class TransplantError(Exception):
    pass

class TooManyCommitsError(Exception):
    pass
