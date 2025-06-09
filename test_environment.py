#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Test Environment Script for Cobaya Memory Testing

This script tests the Docker environment to ensure all tools are properly installed
and configured for Cobaya memory leak testing.

Usage: python test_environment.py [--container CONTAINER_NAME]
       uv run test_environment.py [--container CONTAINER_NAME]
"""

import subprocess
import argparse
import sys
import os


def run_command(cmd, capture_output=True, check=True):
    """Run a command and return the result."""
    try:
        if capture_output:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                check=check
            )
        else:
            # For real-time output, use different approach
            result = subprocess.run(
                cmd,
                shell=True,
                check=check
            )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Error: {e}")
        if hasattr(e, 'stdout') and e.stdout:
            print(f"Stdout: {e.stdout}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Stderr: {e.stderr}")
        raise


def test_environment_in_container(container_name):
    """Test the environment inside the Docker container."""

    print("Running environment tests in Docker container...")
    print("=" * 60)

    try:
        print("Running individual tests...")

        # Test 1: Basic info
        print("Python version:")
        os.system(f'docker run --rm {container_name} python --version')

        print("\nGCC version:")
        os.system(f'docker run --rm {container_name} bash -c "gcc --version | head -1"')

        print("\nGfortran version:")
        os.system(f'docker run --rm {container_name} bash -c "gfortran --version | head -1"')

        print("\nValgrind version:")
        os.system(f'docker run --rm {container_name} valgrind --version')

        print("\nCobaya version:")
        os.system(f'docker run --rm {container_name} python -c "import cobaya; print(cobaya.__version__)"')

        print("\nTesting Cobaya import:")
        os.system(f'docker run --rm {container_name} python -c "import cobaya; print(\'✓ Cobaya import successful\')"')

        print("\nEnvironment variables:")
        os.system(f'docker run --rm {container_name} bash -c "echo COBAYA_PACKAGES_PATH: $COBAYA_PACKAGES_PATH"')
        os.system(f'docker run --rm {container_name} bash -c "echo OMP_NUM_THREADS: $OMP_NUM_THREADS"')

        print()
        print("Available memory profiling commands:")
        print("  valgrind --tool=memcheck --leak-check=full python -m cobaya run mem-leak.yaml")
        print("  heaptrack python -m cobaya run mem-leak.yaml")
        print("  heaptrack python test_camb_example.py")
        print("  gfortran -g -O0 -o test_prog test_fortran_example.f90 && heaptrack ./test_prog")
        print()
        print("Available test workflows:")
        print("  uv run cobaya_memtest.py mem-leak.yaml          # Cobaya workflow")
        print("  uv run cobaya_memtest.py --test-python test.py  # Python test")
        print("  uv run cobaya_memtest.py --test-fortran test.f90 # Fortran test")
        print("=" * 60)
        print("✓ Environment test completed successfully!")
        return True

    except subprocess.CalledProcessError as e:
        print("=" * 60)
        print(f"❌ Environment test failed with return code {e.returncode}")
        return False


def check_docker_image(container_name):
    """Check if Docker image exists."""
    try:
        run_command(f"docker image inspect {container_name}")
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test Cobaya memory testing environment"
    )
    parser.add_argument("--container", default="cobaya-memtest", 
                       help="Docker container name (default: cobaya-memtest)")
    
    args = parser.parse_args()
    container_name = args.container
    
    # Check if Docker image exists
    if not check_docker_image(container_name):
        print(f"Error: Docker image '{container_name}' not found!")
        print(f"Please build it first with: docker build -t {container_name} .")
        print("Or use cobaya-memtest.py --build-only to build the image.")
        sys.exit(1)
    
    print(f"Testing environment in container: {container_name}")
    print()
    
    success = test_environment_in_container(container_name)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
