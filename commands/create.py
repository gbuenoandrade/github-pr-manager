import logging

from .utils import Git, CommandRunner


def run(dep):
    runner = CommandRunner()
    git = Git(runner)
    git.ensure_is_git_repo()
    git.ensure_working_tree_is_clean()
    git.load()

    if dep == 'master':
        base = 'master'
    else:
        pr = git.get_pr_from_number(dep) if dep.isnumeric() else git.get_pr_from_branch(dep)
        base = pr.compare
    git.ensure_branch_is_up_to_date(base)
    current_branch = git.get_current_branch()
    git.push(current_branch)
    _, title, body = git.get_last_commit_info()
    if base != 'master':
        body += f'\n\ndepends on #{pr.number}'
    git.create_pr(base, title, body)
