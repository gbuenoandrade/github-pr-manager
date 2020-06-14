import logging
import json
import os

from collections import defaultdict
from .utils import PR, Git


MERGE_MESSAGE_TEMPLATE = 'Propagate changes from %s via prman 🤖'
EVOLVE_PATH = '.evolve'


def topologically_sorted(prs):
    adj = defaultdict(lambda: [])
    visi = []
    def dfs(cur):
        # Assumes the graph is an arborescence.
        for v in adj[cur]:
            dfs(v)
        visi.append(cur)
    br_to_pr = {}
    for pr in prs:
        adj[pr.base].append(pr.compare)
        br_to_pr[pr.compare] = pr
    dfs('master')
    return [br_to_pr[br] for br in visi[::-1] if br != 'master']


def propagate(git, pr, branch_to_pr_num):
    git.checkout(pr.compare)
    base_pr = f'#{branch_to_pr_num[pr.base]}' if pr.base != 'master' else 'master'
    message = MERGE_MESSAGE_TEMPLATE % base_pr
    if not git.merge(pr.base, message):
        return False
    git.push(pr.compare)
    return True


def save_evolve(cur, rem_prs, branch_to_pr_num):
    state = {'cur': cur, 'rem_prs': rem_prs, 'branch_to_pr_num': branch_to_pr_num}
    with open(EVOLVE_PATH, 'w') as f:
        json.dump(state, f, default=lambda x: x.__dict__)


def load_evolve():
    with open(EVOLVE_PATH, 'r') as f:
        data = json.load(f)
    cur = data['cur']
    rem_prs = [PR(d['number'], d['base'], d['compare'], d['url'], d['title']) for d in data['rem_prs']]
    branch_to_pr_num = data['branch_to_pr_num']
    os.remove(EVOLVE_PATH)
    return cur, rem_prs, branch_to_pr_num


def evolve(git, cur, prs, branch_to_pr_num):
    git.ff_master(cur)
    for idx, pr in enumerate(prs):
        print(f'\nEvolving {pr}')
        if not propagate(git, pr, branch_to_pr_num):
            save_evolve(cur, prs[idx:], branch_to_pr_num)
            print('Run `prman evolve --continue` once you have committed the result')
            exit(1)
    return True


def run(args):
    git = Git()
    git.ensure_is_git_repo()
    git.ensure_working_tree_is_clean()
    is_pending = os.path.isfile(EVOLVE_PATH)
    if not args.cont:
        if is_pending:
            logging.error('pending evolve operation; call `prman evolve --continue` instead')
            exit(1)
        local_branches, cur = git.get_local_branches()
        logging.info(f'current branch: {cur}')
        logging.info(f'local branches: {", ".join([b for b in local_branches])}')
        prs = git.get_prs(local_branches)
        logging.info(f'PRs before sorting: {prs}')
        prs = topologically_sorted(prs)
        logging.info(f'PRs after sorting: {prs}')
        branch_to_pr_num = git.get_branch_to_pr_num(prs)
        logging.info(f'branch to PR num: {branch_to_pr_num}')

        branches = [pr.compare for pr in prs]
        for branch in branches:
            git.ensure_branch_is_up_to_date(branch)
    else:
        if not is_pending:
            logging.error(f'could not find {EVOLVE_PATH}')
            exit(1)
        cur, prs, branch_to_pr_num = load_evolve()
        logging.info(f'current branch: {cur}')

    evolve(git, cur, prs, branch_to_pr_num)
    git.checkout(cur)
