#!/usr/bin/env python3
import argparse
import logging

from commands import evolve, submit, create, update


def main():
    parser = argparse.ArgumentParser(description='Manage GitHub pull requests')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.set_defaults(func=lambda _: parser.print_help())
    subparsers = parser.add_subparsers(help='sub-command help')

    evolve_parser = subparsers.add_parser('evolve', help='propage change to dependent pull requests')
    evolve_parser.add_argument('--continue', dest='cont', action='store_true')
    evolve_parser.set_defaults(func=evolve.run)

    submit_parser = subparsers.add_parser('submit', help='submit pull request')
    submit_parser.set_defaults(func=lambda _ : submit.run())

    create_parser = subparsers.add_parser('create', help='create pull request')
    create_parser.add_argument('-d', '--dependency', default='master', help='pull request to depend on')
    create_parser.set_defaults(func=lambda args : create.run(args.dependency))

    update_parser = subparsers.add_parser('update', help='update %(prog)s')
    update_parser.set_defaults(func=lambda _ : update.run())

    args = parser.parse_args()
    logging.basicConfig(
        format='[%(levelname)s] {%(filename)s:%(lineno)d}: %(message)s',
        level=(logging.DEBUG if args.verbose else logging.WARNING))
    args.func(args)


if __name__ == "__main__":
    main()
