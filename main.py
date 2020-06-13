import argparse
import logging

from commands import evolve, submit, create, update


def main():
    logging.basicConfig(
        format='[%(levelname)s] {%(filename)s:%(lineno)d}: %(message)s', level=logging.DEBUG)
    parser = argparse.ArgumentParser(description='Manage GitHub dependent pull requests')
    subparsers = parser.add_subparsers(help='sub-command help')

    evolve_parser = subparsers.add_parser('evolve', help='propage change to dependent pull requests')
    evolve_parser.set_defaults(func=lambda _ : evolve.run())

    submit_parser = subparsers.add_parser('submit', help='submit pull request')
    submit_parser.set_defaults(func=lambda _ : submit.run())

    create_parser = subparsers.add_parser('create', help='create pull request')
    create_parser.add_argument(
        '-d', '--dependencies', nargs='+', required=True,
        help='pull requests this should depend on')
    create_parser.set_defaults(func=lambda args : create.run(args.dependencies))

    update_parser = subparsers.add_parser('update')
    update_parser.set_defaults(func=lambda _ : update.run())

    args = parser.parse_args()
    try:
        args.func(args)
    except AttributeError:
        parser.print_help()
        parser.exit()


if __name__ == "__main__":
    main()
