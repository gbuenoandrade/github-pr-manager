import logging
import json
import os

from .utils import PR, Git, CommandRunner


MERGE_MESSAGE_TEMPLATE = 'Propagate changes from %s via prman 🤖'
EVOLVE_PATH = '.prman_evolve'


def save_evolve(initial_branch, sorted_prs, idx):
    state = {'initial_branch': initial_branch, 'sorted_prs': sorted_prs, 'idx': idx}
    with open(EVOLVE_PATH, 'w') as f:
        json.dump(state, f, default=lambda x: x.__dict__)


def load_evolve():
    with open(EVOLVE_PATH, 'r') as f:
        data = json.load(f)
    initial_branch = data['initial_branch']
    sorted_prs = [PR.from_dict(d) for d in data['sorted_prs']]
    idx = data['idx']
    os.remove(EVOLVE_PATH)
    return initial_branch, sorted_prs, idx, 


def propagate(git, pr):
    git.checkout(pr.compare)
    base_pr = f'#{git.get_pr_from_branch(pr.base).number}' if pr.base != 'master' else 'master'
    message = MERGE_MESSAGE_TEMPLATE % base_pr
    if not git.merge(pr.base, message):
        return False
    git.push(pr.compare)
    return True


def evolve(git, initial_branch, sorted_prs, start):
    git.ff_master()
    for idx in range(start, len(sorted_prs)):
        pr = sorted_prs[idx]
        print(f'\nEvolving {pr}')
        if not propagate(git, pr):
            save_evolve(initial_branch, sorted_prs, idx)
            print('Run `prman evolve --continue` once you have committed the result')
            exit(1)
    return True


def run(is_continue):
    is_evolving = os.path.isfile(EVOLVE_PATH)
    if is_continue and not is_evolving:
        logging.error('no evolve in progress?')
        exit(1)
    if is_evolving and not is_continue:
        logging.error('pending evolve operation; run `prman evolve --continue` instead')
        exit(1)

    runner = CommandRunner()
    git = Git(runner)
    git.ensure_is_git_repo()
    git.ensure_working_tree_is_clean()
    if is_continue:
        initial_branch, sorted_prs, start = load_evolve()
        git.load(sorted_prs)
    else:
        git.load()
        git.ensure_prs_are_up_to_date()
        initial_branch = git.get_current_branch()
        sorted_prs = git.get_sorted_prs()
        start = 0
    evolve(git, initial_branch, sorted_prs, start)
    git.checkout(initial_branch)
