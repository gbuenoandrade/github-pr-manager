import logging
import os
import re
import shlex
import subprocess

from collections import defaultdict


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


class CommandRunner(object):
    @staticmethod
    def run(cmd, interactive=False, check=True):
        logging.info(f'executing command "{cmd}"')
        args = shlex.split(cmd)
        output = ''
        if interactive:
            p = subprocess.run(args, check=False)
            out = None
            err = None
        else:
            p = subprocess.run(
                    args, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out = p.stdout.decode('utf-8').strip()
            if out != '':
                output += f'\nstdout:\n{out}'
            err = p.stderr.decode('utf-8').strip()
            if err != '':
                output += f'\nstderr:\n{err}'
        ret = p.returncode
        logging.debug(f'"{cmd}"" exited with status {ret}{output}')
        if check and ret:
            logging.error(f'command "{cmd}" returned non-zero exit status {ret}{output}')
            exit(1)
        return out, err, ret


class Git(object):
    def __init__(self, runner):
        self.runner = runner
        self._number_to_pr = None
        self._branch_to_pr = None

    @staticmethod
    def ensure_is_git_repo():
        if not os.path.isdir('.git'):
            logging.error('not a git repository')
            exit(1)

    def load(self, prs=None):
        if not prs:
            prs = self._fetch_prs()
        self._number_to_pr = {pr.number: pr for pr in prs}
        self._branch_to_pr = {pr.compare: pr for pr in prs}

    def ensure_working_tree_is_clean(self):
        out, _, _ = self.runner.run('git status')
        if 'working tree clean' not in out:
            logging.error('working tree is dirty')
            exit(1)

    def ensure_branch_is_up_to_date(self, branch):
        _, err, ret = self.runner.run(f'git push origin --dry-run {branch}', check=False)
        if ret or 'Everything up-to-date' not in err:
            logging.error(f'{branch} is not up-to-date')
            exit(1)

    def ensure_prs_are_up_to_date(self):
        for pr in self._number_to_pr.values():
            self.ensure_branch_is_up_to_date(pr.compare)

    def checkout(self, branch):
        self.runner.run(f'git checkout {branch}')

    def push(self, branch):
        self.runner.run(f'git push origin {branch}')

    def pull(self, branch, message):
        self.runner.run(f'git pull origin {branch} --no-edit')
        self.runner.run(f'git commit --amend -m "{message}"')

    def merge(self, branch, message):
        _, _, ret = self.runner.run(
                f'git merge {branch} -m "{message}"', interactive=True, check=False)
        return not ret

    def get_last_commit_info(self):
        separator = '$$'
        format = f'format:%H{separator}%s{separator}%b'
        out, _, _ = self.runner.run(f'git log -1 --pretty="{format}"')
        return out.split(separator)

    def get_current_branch(self):
        out, _, _ = self.runner.run('git rev-parse --abbrev-ref HEAD')
        return out

    # Rebase the range of commits whose parent is 'old_base' up to 'until' on top of 'new_base'.
    def rebase(self, new_base, old_base, until):
        self.runner.run(f'git rebase --onto {new_base} {old_base} {until}')

    def ff_master(self):
        print('Fast-forwarding master')
        if self.get_current_branch() == 'master':
            self.runner.run('git pull origin master', interactive=True)
        else:
            self.runner.run('git fetch origin master:master', interactive=True)

    def create_pr(self, base, title, body):
        self.runner.run(f'gh pr create --base {base} --title "{title}" --body "{body}" --web',
                interactive=True)

    def submit_pr(self):
        out, err, ret = self.runner.run(
                'gh pr merge --squash --delete-branch', check=False)
        # It is safe to ignore the "Reference does not exist" error.
        # That happens when the remote branch had already been deleted.
        if ret and 'Reference does not exist' not in err:
            logging.error(err)
            return(1)
        print(out)

    def get_sorted_prs(self):
        return topologically_sorted(self._number_to_pr.values())

    def get_pr_from_branch(self, branch):
        pr = self._branch_to_pr.get(branch)
        if not pr:
            self._call_missing_pr_error(branch)
        return pr

    def get_pr_from_number(self, number):
        pr = self._number_to_pr.get(number)
        if not pr:
            self._call_missing_pr_error(number)
        return pr

    def get_dependents(self, head_branch):
        dependents = []
        for pr in self._number_to_pr.values():
            if pr.base == head_branch:
                dependents.append(pr)
        return dependents

    def _call_missing_pr_error(self, pr_ref):
        prs = [f'(#{pr.number}|{pr.compare})' for pr in self.get_sorted_prs()]
        logging.error(f"could not find {pr_ref} among local PRs: {', '.join(prs)}")
        exit(1)

    def _fetch_prs(self):
        local_branches = self._get_local_branches()
        prs = []
        pr_list, _, _ = self.runner.run('gh pr list --state open')
        for l in pr_list.splitlines():
            number = l.strip().split()[0]
            pr_view, _, _ =  self.runner.run(f'gh pr view {number}')
            title = pr_view.partition('\n')[0]
            m = re.search(r'into (\S+) from (\S+)', pr_view)
            base, compare = m.groups()
            if base not in local_branches or compare not in local_branches:
                continue
            m = re.search(r'request on GitHub: (https://\S+)', pr_view)
            url = m.groups()[0]
            prs.append(PR(number, base, compare, url, title))
        return prs

    def _get_local_branches(self):
        branches = set()
        out, _, _ = self.runner.run('git branch')
        for l in out.splitlines():
            branch = l.split()[-1].strip()
            branches.add(branch)
        return branches


class PR(object):
    def __init__(self, number, base, compare, url, title):
        self.number = number
        self.base = base
        self.compare = compare
        self.url = url
        self.title = title

    @staticmethod
    def from_dict(d):
        return PR(d['number'], d['base'], d['compare'], d['url'], d['title'])

    def __repr__(self):
        return f'{self.title} #{self.number}: {self.base} <- {self.compare} ({self.url})'
