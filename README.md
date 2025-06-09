# Cobaya Memory Leak Testing

Docker environment for detecting and analyzing memory leaks in Cobaya runs, with focus on CAMBLIB.SO (Fortran) leaks.

## Quick Start

```bash
# Automatic workflow - builds image if needed
uv run cobaya_memtest.py mem-leak.yaml
```

## Commands

### Full Workflow
```bash
uv run cobaya_memtest.py your-config.yaml
```
This command will:
1. Automatically build Docker image if it doesn't exist
2. Run Cobaya with heaptrack memory profiling
3. Generate a clean leak summary report
4. Show key findings with leak sizes and function names

### Build Management
```bash
# Build image only
uv run cobaya_memtest.py --build-only

# Force rebuild (useful when config changes)
uv run cobaya_memtest.py --force-rebuild mem-leak.yaml

# Test environment setup (shows versions and validates installation)
uv run cobaya_memtest.py --test-environment
```

### Environment Testing Output
The `--test-environment` option provides detailed information:
```
Python version: Python 3.10.12
GCC version: gcc (Ubuntu 12.3.0-1ubuntu1~22.04) 12.3.0
Gfortran version: GNU Fortran (Ubuntu 12.3.0-1ubuntu1~22.04) 12.3.0
Valgrind version: valgrind-3.18.1
Cobaya version: 3.5.7
✓ Cobaya import successful
Environment variables: COBAYA_PACKAGES_PATH, OMP_NUM_THREADS
```

### Analysis Only
```bash
# Analyze existing heaptrack file
uv run cobaya_memtest.py --analyze-only heaptrack_file.gz.gz
```

## Example Output

```
=== KEY FINDINGS ===

Top 5 Memory Leaks:
  1. 13.30M - __results_MOD_init_cltransfer (CAMBLIB.SO)
  2. 5.92M - 0x571a63ea5170
  3. 2.12M - __spherbessels_MOD_initspherbessels (CAMBLIB.SO)
  4. 1.96M - PyObject_Malloc
  5. 1.07M - PyType_GenericAlloc

CAMBLIB.SO Summary:
  - 3 different functions with leaks
  - ~15.7M total leaked memory
  - Top CAMB leak: 13.30M from __results_MOD_init_cltransfer
```

## Generated Report

The script creates a detailed report (`leak_summary_TIMESTAMP.txt`) with:

- **Overall statistics**: Total allocations, peak memory, total leaks
- **Top memory leaks**: Sorted by size with leak count and function names
- **Detailed stack traces**: Complete call stacks for the top 5 memory leaks
- **CAMBLIB.SO specific leaks**: Fortran-related leaks separated from Python
- **Specific functions**: Analysis of known problematic functions with stack traces
- **Console summary**: Shows stack trace for the largest leak in terminal output

## Configuration

The Docker image can be customized via `docker-config.yaml`:

```yaml
# Docker image settings
image_name: "cobaya-memtest"

# Build arguments - customize versions
build_args:
  UBUNTU_VERSION: "22.04"    # 20.04, 22.04, 24.04
  PYTHON_VERSION: "3.10"     # 3.10, 3.11, 3.12
  GCC_VERSION: "12"          # 11, 12, 13
```

### Manual Docker Build (Advanced)
```bash
# Custom versions
docker build -t cobaya-memtest \
  --build-arg PYTHON_VERSION=3.11 \
  --build-arg GCC_VERSION=13 .
```

## Environment

- **Configurable versions**: Ubuntu (20.04/22.04/24.04), Python (3.10/3.11/3.12), GCC (11/12/13)
- **Default**: Ubuntu 22.04, Python 3.10, GCC 12.3.0 with gfortran
- **Cobaya** with CAMB and Planck 2018 data pre-installed
- **Memory tools**: Valgrind and Heaptrack for comprehensive profiling
- **Cross-platform** via Docker and `uv run`

## Key Features

- **Auto-build**: Automatically builds Docker image if missing
- **Persistent images**: Images are not deleted between runs for efficiency
- **Force rebuild**: Option to rebuild when configuration changes
- **Environment testing**: Built-in environment validation
- **Actual leak focus**: Reports leak count, size, and function names (not just allocations)
- **Stack trace analysis**: Complete call stacks for top leaks showing exact code paths
- **CAMBLIB.SO analysis**: Identifies Fortran memory leaks in CAMB with detailed traces
- **Clean reporting**: Easy-to-read summaries with key findings and stack traces
- **Cross-platform**: Works on Windows, Linux, macOS

## Advanced Usage

### Direct Analysis Scripts
```bash
# Direct heaptrack analysis
uv run leak_summary.py heaptrack_file.gz.gz

# Environment testing only
uv run test_environment.py --container cobaya-memtest
```
