# parallel-rm-rf
Tool for faster parallel directories removal in Unix systems (parallel rm -rf)

## Installation

```bash
pip install git+https://github.com/boomb0om/parallel-rm-rf.git
```

## Usage

```bash
python -m parallel_rm_rf <directory> -p <number_of_processes> -v
```

To print help information use:
```bash
python -m parallel_rm_rf --help
```

CLI parameters:
1. `<directory>` - path to directory to remove
2. `-p` or `--processes` - number of parallel processes to use (default=8)
3. `-v` or `--verbose` - print information about removal

### Example

```bash
python -m parallel_rm_rf src/test -p 32
```
