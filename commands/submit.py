import logging

from .utils import Git, CommandRunner


MERGE_MESSAGE_TEMPLATE = 'Rebase after #%s submission via prman 🤖'


def run():
    runner = CommandRunner()
    git = Git(runner)
    git.ensure_is_git_repo()
    git.ensure_working_tree_is_clean()
    git.load()
    # TODO(guiandrade): Ensure repo is "evolved"

    branch = git.get_current_branch()
    pr = git.get_pr_from_branch(branch)
    if pr.base != 'master':
        logging.error(f'#{pr.number} has base ref {pr.base}; only merging into master is allowed')
        exit(1)
    print(f'Submitting {pr}')
    base_commit, _, _ = git.get_last_commit_info()
    git.submit_pr()
    git.ff_master()
    deps = git.get_dependents(pr.compare)
    message = MERGE_MESSAGE_TEMPLATE % pr.number
    for dep in deps:
        print(f'Updating {dep}')
        git.rebase('master', base_commit, dep.compare)
        git.pull(dep.compare, message)
        git.push(dep.compare)
