#!/usr/bin/env python3
# /// script
# dependencies = [
#   "pyyaml",
# ]
# ///
"""
Cobaya Memory Leak Testing - Complete Workflow

This script provides a complete workflow for Cobaya memory leak testing:
1. Automatically build Docker image if needed
2. Run Cobaya with heaptrack profiling
3. Run Python test files with heaptrack profiling
4. Compile and run Fortran tests with heaptrack profiling
5. Analyze the results and generate reports
6. Test environment setup

Usage: python cobaya_memtest.py <yaml_file> [options]
       uv run cobaya_memtest.py <yaml_file> [options]

Examples:
  python cobaya_memtest.py mem-leak.yaml                    # Full Cobaya workflow
  python cobaya_memtest.py --test-python test_camb.py       # Test Python file
  python cobaya_memtest.py --test-fortran test_prog.f90     # Test Fortran file
  python cobaya_memtest.py --build-only                     # Just build image
  python cobaya_memtest.py --test-environment               # Test environment
  python cobaya_memtest.py mem-leak.yaml --force-rebuild    # Rebuild image first
"""

import sys
import os
import subprocess
import datetime
import argparse

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def run_command(cmd, capture_output=True, check=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=capture_output, 
            text=True, 
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Error: {e}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        raise


def load_config(config_file="docker-config.yaml"):
    """Load configuration from YAML file."""
    default_config = {
        'image_name': 'cobaya-memtest',
        'build_args': {
            'UBUNTU_VERSION': '22.04',
            'PYTHON_VERSION': '3.10',
            'GCC_VERSION': '12'
        }
    }

    if os.path.exists(config_file) and HAS_YAML:
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                    elif isinstance(value, dict) and isinstance(config[key], dict):
                        for subkey, subvalue in value.items():
                            if subkey not in config[key]:
                                config[key][subkey] = subvalue
                return config
        except Exception as e:
            print(f"Warning: Could not load config file {config_file}: {e}")
            print("Using default configuration.")
    elif os.path.exists(config_file) and not HAS_YAML:
        print(f"Warning: YAML module not available. Cannot load {config_file}.")
        print("Using default configuration.")

    return default_config


def check_docker_image(container_name):
    """Check if Docker image exists."""
    try:
        run_command(f"docker image inspect {container_name}")
        return True
    except subprocess.CalledProcessError:
        return False


def build_docker_image(container_name, config, force_rebuild=False):
    """Build Docker image with specified configuration."""
    if not force_rebuild and check_docker_image(container_name):
        print(f"✓ Docker image '{container_name}' already exists.")
        return True

    print(f"Building Docker image '{container_name}'...")

    # Prepare build arguments
    build_args = []
    for key, value in config.get('build_args', {}).items():
        build_args.extend(['--build-arg', f'{key}={value}'])

    # Build command
    cmd_parts = ['docker', 'build', '-t', container_name] + build_args + ['.']
    cmd = ' '.join(cmd_parts)

    print(f"Build command: {cmd}")
    print("This may take several minutes...")

    try:
        run_command(cmd, capture_output=False)
        print(f"✓ Docker image '{container_name}' built successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to build Docker image: {e}")
        return False


def run_cobaya_with_heaptrack(yaml_file, container_name):
    """Run Cobaya with heaptrack profiling."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"heaptrack_cobaya_{timestamp}.gz"

    print("Running Cobaya with heaptrack...")
    print("This may take several minutes depending on the configuration...")

    # Use the working Docker command format
    docker_cmd = f"""docker run --rm -v "{os.getcwd()}:/workspace" -w /workspace {container_name} bash -c "export PYTHONPATH=/opt/cobaya-packages/code/CAMB:$PYTHONPATH && export COBAYA_PACKAGES_PATH=/opt/cobaya-packages && heaptrack --output {output_file} python -m cobaya run {yaml_file} --force" """

    print("Running command...")
    try:
        run_command(docker_cmd, capture_output=False)
    except subprocess.CalledProcessError as e:
        print(f"Docker command failed with return code {e.returncode}")
        raise

    # heaptrack automatically adds .gz extension
    expected_file = f"{output_file}.gz"
    if not os.path.exists(expected_file):
        raise FileNotFoundError(f"Heaptrack output file not found: {expected_file}")

    print(f"✓ Heaptrack data saved to: {expected_file}")
    return expected_file


def run_python_test_with_heaptrack(test_file, container_name):
    """Run Python test file with heaptrack profiling."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"heaptrack_python_{timestamp}.gz"

    print(f"Running Python test file '{test_file}' with heaptrack...")
    print("This may take several minutes depending on the test...")

    # Use the working Docker command format
    docker_cmd = f"""docker run --rm -v "{os.getcwd()}:/workspace" -w /workspace {container_name} bash -c "export PYTHONPATH=/opt/cobaya-packages/code/CAMB:$PYTHONPATH && export COBAYA_PACKAGES_PATH=/opt/cobaya-packages && heaptrack --output {output_file} python {test_file}" """

    print("Running command...")
    try:
        run_command(docker_cmd, capture_output=False)
    except subprocess.CalledProcessError as e:
        print(f"Docker command failed with return code {e.returncode}")
        raise

    # heaptrack automatically adds .gz extension
    expected_file = f"{output_file}.gz"
    if not os.path.exists(expected_file):
        raise FileNotFoundError(f"Heaptrack output file not found: {expected_file}")

    print(f"✓ Heaptrack data saved to: {expected_file}")
    return expected_file


def compile_fortran_test(fortran_file, container_name, compile_only=False):
    """Compile Fortran test file and optionally run with heaptrack."""
    # Extract base name for executable
    base_name = os.path.splitext(os.path.basename(fortran_file))[0]
    executable = f"{base_name}_test"

    print(f"Compiling Fortran file '{fortran_file}'...")

    # Compile the Fortran file
    compile_cmd = f"""docker run --rm -v "{os.getcwd()}:/workspace" -w /workspace {container_name} bash -c "gfortran -g -O0 -o {executable} {fortran_file}" """

    try:
        run_command(compile_cmd, capture_output=False)
        print(f"✓ Fortran file compiled successfully: {executable}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Compilation failed with return code {e.returncode}")
        raise

    if compile_only:
        return executable

    # Run with heaptrack
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"heaptrack_fortran_{timestamp}.gz"

    print(f"Running Fortran executable '{executable}' with heaptrack...")

    run_cmd = f"""docker run --rm -v "{os.getcwd()}:/workspace" -w /workspace {container_name} bash -c "heaptrack --output {output_file} ./{executable}" """

    try:
        run_command(run_cmd, capture_output=False)
    except subprocess.CalledProcessError as e:
        print(f"Docker command failed with return code {e.returncode}")
        raise

    # heaptrack automatically adds .gz extension
    expected_file = f"{output_file}.gz"
    if not os.path.exists(expected_file):
        raise FileNotFoundError(f"Heaptrack output file not found: {expected_file}")

    print(f"✓ Heaptrack data saved to: {expected_file}")
    return expected_file


def analyze_heaptrack_data(heaptrack_file, container_name):
    """Analyze heaptrack data using the leak_summary.py script."""
    print(f"\nAnalyzing heaptrack data: {heaptrack_file}")

    # Run the leak summary script
    analysis_cmd = f"python leak_summary.py {heaptrack_file} --container {container_name}"

    try:
        run_command(analysis_cmd, capture_output=False)
        return True
    except subprocess.CalledProcessError:
        print("Error running leak summary script. Trying with uv run...")
        try:
            analysis_cmd = f"uv run leak_summary.py {heaptrack_file} --container {container_name}"
            run_command(analysis_cmd, capture_output=False)
            return True
        except subprocess.CalledProcessError:
            print("Error: Could not run leak summary script with either python or uv run")
            return False


def run_test_environment(container_name):
    """Run the test environment script."""
    try:
        # Try to run the test environment script
        if os.path.exists("test_environment.py"):
            cmd = f"python test_environment.py --container {container_name}"
            try:
                run_command(cmd, capture_output=False)
                return True
            except subprocess.CalledProcessError:
                # Try with uv run
                cmd = f"uv run test_environment.py --container {container_name}"
                run_command(cmd, capture_output=False)
                return True
        else:
            print("Warning: test_environment.py not found. Running basic test...")
            # Fallback to basic test - show output
            test_script = '''
echo "=== Basic Environment Test ==="
echo "Python: $(python --version)"
echo "GCC: $(gcc --version | head -1)"
echo "Cobaya: $(python -c 'import cobaya; print(cobaya.__version__)')"
echo "✓ Basic test completed"
'''
            test_cmd = f'''docker run --rm {container_name} bash -c "{test_script}"'''
            run_command(test_cmd, capture_output=False)
            return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Test environment failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Complete Cobaya memory leak testing workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s mem-leak.yaml                    # Full Cobaya workflow
  %(prog)s --test-python test_camb.py       # Test Python file
  %(prog)s --test-fortran test_prog.f90     # Test Fortran file
  %(prog)s --compile-only test_prog.f90     # Just compile Fortran
  %(prog)s --build-only                     # Just build image
  %(prog)s --test-environment               # Test environment
  %(prog)s mem-leak.yaml --force-rebuild    # Rebuild image first
  %(prog)s --analyze-only heaptrack_file.gz # Analyze existing file
        """
    )
    parser.add_argument("yaml_file", nargs='?', help="YAML configuration file for Cobaya")
    parser.add_argument("--container", default=None,
                       help="Docker container name (default: from config)")
    parser.add_argument("--config", default="docker-config.yaml",
                       help="Configuration file (default: docker-config.yaml)")
    parser.add_argument("--test-python",
                       help="Run Python test file with heaptrack profiling")
    parser.add_argument("--test-fortran",
                       help="Compile and run Fortran test file with heaptrack profiling")
    parser.add_argument("--compile-only",
                       help="Only compile Fortran file (don't run with heaptrack)")
    parser.add_argument("--analyze-only",
                       help="Only analyze existing heaptrack file (skip Cobaya run)")
    parser.add_argument("--build-only", action="store_true",
                       help="Only build Docker image (skip running)")
    parser.add_argument("--force-rebuild", action="store_true",
                       help="Force rebuild of Docker image")
    parser.add_argument("--test-environment", action="store_true",
                       help="Test the Docker environment setup")

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)
    container_name = args.container or config.get('image_name', 'cobaya-memtest')

    print("=== Cobaya Memory Leak Testing Workflow ===")
    print(f"Container: {container_name}")
    print(f"Config file: {args.config}")
    print()

    # Handle build-only option
    if args.build_only:
        print("Building Docker image only...")
        success = build_docker_image(container_name, config, force_rebuild=args.force_rebuild)
        if success:
            print("✓ Build completed successfully!")
        else:
            print("❌ Build failed!")
            sys.exit(1)
        return

    # Handle test-environment option
    if args.test_environment:
        print("Testing environment...")
        # Build image if it doesn't exist
        if not check_docker_image(container_name):
            print(f"Docker image '{container_name}' not found. Building...")
            if not build_docker_image(container_name, config):
                print("❌ Failed to build Docker image!")
                sys.exit(1)

        success = run_test_environment(container_name)
        if not success:
            sys.exit(1)
        return

    # Handle compile-only option
    if args.compile_only:
        if not os.path.exists(args.compile_only):
            print(f"Error: Fortran file '{args.compile_only}' not found!")
            sys.exit(1)

        # Build image if it doesn't exist
        if not check_docker_image(container_name):
            print(f"Docker image '{container_name}' not found. Building...")
            if not build_docker_image(container_name, config):
                print("❌ Failed to build Docker image!")
                sys.exit(1)

        try:
            executable = compile_fortran_test(args.compile_only, container_name, compile_only=True)
            print(f"✓ Compilation completed successfully: {executable}")
        except Exception as e:
            print(f"❌ Compilation failed: {e}")
            sys.exit(1)
        return

    # For other operations, we need a file
    if not args.yaml_file and not args.analyze_only and not args.test_python and not args.test_fortran:
        print("Error: Input file required (YAML for Cobaya, Python test file, or Fortran test file).")
        print("Use --help for usage information.")
        sys.exit(1)

    # Build Docker image if needed (for all operations except analyze-only)
    if not args.analyze_only:
        if not check_docker_image(container_name):
            print(f"Docker image '{container_name}' not found. Building...")
            if not build_docker_image(container_name, config):
                print("❌ Failed to build Docker image!")
                sys.exit(1)
        elif args.force_rebuild:
            print("Force rebuilding Docker image...")
            if not build_docker_image(container_name, config, force_rebuild=True):
                print("❌ Failed to rebuild Docker image!")
                sys.exit(1)

    try:
        if args.analyze_only:
            # Only analyze existing file
            if not os.path.exists(args.analyze_only):
                print(f"Error: Heaptrack file '{args.analyze_only}' not found!")
                sys.exit(1)

            print(f"Analyzing existing heaptrack file: {args.analyze_only}")
            success = analyze_heaptrack_data(args.analyze_only, container_name)

        elif args.test_python:
            # Test Python file workflow
            if not os.path.exists(args.test_python):
                print(f"Error: Python test file '{args.test_python}' not found!")
                sys.exit(1)

            print(f"Input file: {args.test_python}")

            # Step 1: Run Python test with heaptrack
            print("\n" + "="*50)
            print("STEP 1: Running Python test with heaptrack")
            print("="*50)
            heaptrack_file = run_python_test_with_heaptrack(args.test_python, container_name)

            # Step 2: Analyze results
            print("\n" + "="*50)
            print("STEP 2: Analyzing heaptrack data")
            print("="*50)
            success = analyze_heaptrack_data(heaptrack_file, container_name)

        elif args.test_fortran:
            # Test Fortran file workflow
            if not os.path.exists(args.test_fortran):
                print(f"Error: Fortran test file '{args.test_fortran}' not found!")
                sys.exit(1)

            print(f"Input file: {args.test_fortran}")

            # Step 1: Compile and run Fortran test with heaptrack
            print("\n" + "="*50)
            print("STEP 1: Compiling and running Fortran test with heaptrack")
            print("="*50)
            heaptrack_file = compile_fortran_test(args.test_fortran, container_name)

            # Step 2: Analyze results
            print("\n" + "="*50)
            print("STEP 2: Analyzing heaptrack data")
            print("="*50)
            success = analyze_heaptrack_data(heaptrack_file, container_name)

        else:
            # Full Cobaya workflow: run Cobaya then analyze
            yaml_file = args.yaml_file
            if not os.path.exists(yaml_file):
                print(f"Error: YAML file '{yaml_file}' not found!")
                sys.exit(1)

            print(f"Input file: {yaml_file}")

            # Step 1: Run Cobaya with heaptrack
            print("\n" + "="*50)
            print("STEP 1: Running Cobaya with heaptrack")
            print("="*50)
            heaptrack_file = run_cobaya_with_heaptrack(yaml_file, container_name)

            # Step 2: Analyze results
            print("\n" + "="*50)
            print("STEP 2: Analyzing heaptrack data")
            print("="*50)
            success = analyze_heaptrack_data(heaptrack_file, container_name)
        
        if success:
            print("\n" + "="*50)
            print("WORKFLOW COMPLETED SUCCESSFULLY!")
            print("="*50)
            print("\nCheck the analysis_results_* directory for detailed reports.")
            print("Key files:")
            print("- memory_report.txt: Detailed heaptrack analysis")
            print("- summary.txt: Summary and instructions")
            print("\nFor interactive analysis, use:")
            if args.analyze_only:
                print(f"  heaptrack_gui {args.analyze_only}")
            else:
                print(f"  heaptrack_gui {heaptrack_file}")
        else:
            print("\n❌ Analysis step failed. Check the error messages above.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
