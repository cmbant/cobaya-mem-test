# Cobaya Memory Leak Testing

Docker environment for detecting and analyzing memory leaks in Cobaya runs, with focus on CAMBLIB.SO (Fortran) leaks.

## Quick Start

```bash
# 1. Build the Docker image
docker build -t cobaya-memtest .

# 2. Run memory leak analysis on your YAML file
uv run cobaya_memtest.py mem-leak.yaml
```

## Main Command

```bash
uv run cobaya_memtest.py your-config.yaml
```

This command will:
1. Run Cobaya with heaptrack memory profiling
2. Generate a clean leak summary report
3. Show key findings with leak sizes and function names

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
- **CAMBLIB.SO specific leaks**: Fortran-related leaks separated from Python
- **Specific functions**: Analysis of known problematic functions

## Additional Commands

```bash
# Analyze existing heaptrack file
uv run leak_summary.py heaptrack_file.gz.gz

# Analyze existing data without re-running Cobaya
uv run cobaya_memtest.py --analyze-only heaptrack_file.gz.gz your-config.yaml
```

## Environment

- **Ubuntu 22.04** with GCC 12.3.0, gfortran, Python 3.10
- **Cobaya** with CAMB and Planck 2018 data pre-installed
- **Heaptrack** for memory profiling
- **Cross-platform** via Docker and `uv run`

## Key Features

- **Actual leak focus**: Reports leak count, size, and function names (not just allocations)
- **CAMBLIB.SO analysis**: Identifies Fortran memory leaks in CAMB
- **Clean reporting**: Easy-to-read summaries with key findings
- **Cross-platform**: Works on Windows, Linux, macOS
