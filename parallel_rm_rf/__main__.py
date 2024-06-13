import asyncio
import argparse

from parallel_rm_rf.remover import parallel_rm_rf


def main():
    parser = argparse.ArgumentParser(
        prog='parallel-rm-rf',
        description='Parallel rm rf command for faster delete in Unix systems'
    )
    parser.add_argument('dirpath', type=str, help="Path to directory to delete")
    parser.add_argument('-p', '--processes', type=int, help='Number of parallel processes', default=8)
    parser.add_argument('-v', '--verbose', action='store_true', help='Print additional info')
    args = parser.parse_args()

    parallel_rm_rf(
        args.dirpath,
        args.processes,
        verbose=args.verbose
    )


if __name__ == "__main__":
    main()