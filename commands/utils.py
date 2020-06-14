import logging
import os
import re
import shlex
import subprocess


class Git(object):
    @staticmethod
    def ensure_is_git_repo():
        if not os.path.isdir('.git'):
            logging.error('not a git repository')
            exit(1)

    @staticmethod
    def ensure_working_tree_is_clean():
        out, _, _ = run_cmd('git status')
        if 'working tree clean' not in out:
            logging.error('working tree is dirty')
            exit(1)

    @staticmethod
    def ensure_branch_is_up_to_date(branch):
        _, err, ret = run_cmd(f'git push origin --dry-run {branch}', check=False)
        if ret or 'Everything up-to-date' not in err:
            logging.error(f'{branch} is not up-to-date')
            exit(1)

    @staticmethod
    def get_local_branches():
        branches = set()
        out, _, _ = run_cmd('git branch')
        current = None
        for l in out.splitlines():
            branch = l.split()[-1].strip()
            branches.add(branch)
            if '*' in l:
                current = branch
        return branches, current

    @staticmethod
    def get_prs(branches):
        prs = []
        pr_list, _, _ = run_cmd('gh pr list --state open')
        for l in pr_list.splitlines():
            number = l.strip().split()[0]
            pr_view, _, _ =  run_cmd(f'gh pr view {number}')
            title = pr_view.partition('\n')[0]
            m = re.search(r'into (\S+) from (\S+)', pr_view)
            base, compare = m.groups()
            if base not in branches or compare not in branches:
                continue
            m = re.search(r'request on GitHub: (https://\S+)', pr_view)
            url = m.groups()[0]
            prs.append(PR(number, base, compare, url, title))
        return prs

    @staticmethod
    def get_branch_to_pr_num(prs):
        return {pr.compare: pr.number for pr in prs}

    @staticmethod
    def get_pr_num_to_branch(prs):
        return {pr.number: pr.compare for pr in prs}

    @staticmethod
    def checkout(branch):
        run_cmd(f'git checkout {branch}')

    @staticmethod
    def push(branch):
        run_cmd(f'git push origin {branch}')

    @staticmethod
    def ff_master(cur):
        print('Fast-forwarding master')
        if cur == 'master':
            run_cmd('git pull origin master', interactive=True)
        else:
            run_cmd('git fetch origin master:master', interactive=True)

    @staticmethod
    def merge(branch, message):
        _, _, ret = run_cmd(
                f'git merge {branch} -m "{message}"', interactive=True, check=False)
        return not ret

    @staticmethod
    def get_last_commit():
        out, _, _ = run_cmd("git log -1 --pretty='format:%s%n%b'")
        tokens = out.partition('\n')
        title = tokens[0]
        body = tokens[-1]
        return title, body
    
    @staticmethod
    def create_pr(base, title, body):
        run_cmd(f'gh pr create --base {base} --title "{title}" --body "{body}" --web',
                interactive=True)


class PR(object):
    def __init__(self, number, base, compare, url, title):
        self.number = number
        self.base = base
        self.compare = compare
        self.url = url
        self.title = title

    def __repr__(self):
        return f'{self.title} #{self.number}: {self.base} <- {self.compare} ({self.url})'


def run_cmd(cmd, interactive=False, check=True):
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
