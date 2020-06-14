import logging

from .utils import Git


def run(dep):
    git = Git()
    git.ensure_is_git_repo()
    git.ensure_working_tree_is_clean()

    branches, cur = git.get_local_branches()
    if dep != 'master':
        prs = git.get_prs(branches)
        pr_to_branch = git.get_pr_num_to_branch(prs)
        if dep not in pr_to_branch:
            prs_str = ', '.join([f'#{pr.number}' for pr in prs])
            logging.error(f'could not find #{dep} among checked out PRs: {prs_str}')
            exit(1)
        base = pr_to_branch[dep]
    else:
        base = 'master'
    git.push(cur)
    title, body = git.get_last_commit()
    if base != 'master':
        body += f'\n\ndepends on #{dep}'
    git.create_pr(base, title, body)
