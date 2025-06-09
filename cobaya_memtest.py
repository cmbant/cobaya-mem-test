#!/usr/bin/env python3
"""
Cobaya Memory Leak Testing - Complete Workflow

This script provides a complete workflow for Cobaya memory leak testing:
1. Run Cobaya with heaptrack profiling
2. Analyze the results and generate reports

Usage: python cobaya_memtest.py <yaml_file>
       uv run cobaya_memtest.py <yaml_file>

Example: python cobaya_memtest.py mem-leak.yaml
"""

import sys
import os
import subprocess
import datetime
import argparse


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


def check_docker_image(container_name):
    """Check if Docker image exists."""
    try:
        run_command(f"docker image inspect {container_name}")
        return True
    except subprocess.CalledProcessError:
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


def main():
    parser = argparse.ArgumentParser(
        description="Complete Cobaya memory leak testing workflow"
    )
    parser.add_argument("yaml_file", help="YAML configuration file for Cobaya")
    parser.add_argument("--container", default="cobaya-memtest", 
                       help="Docker container name (default: cobaya-memtest)")
    parser.add_argument("--analyze-only", 
                       help="Only analyze existing heaptrack file (skip Cobaya run)")
    
    args = parser.parse_args()
    
    yaml_file = args.yaml_file
    container_name = args.container
    
    # Check if Docker image exists
    if not check_docker_image(container_name):
        print(f"Error: Docker image '{container_name}' not found!")
        print(f"Please build it first with: docker build -t {container_name} .")
        sys.exit(1)
    
    print("=== Cobaya Memory Leak Testing Workflow ===")
    print(f"Container: {container_name}")
    print()
    
    try:
        if args.analyze_only:
            # Only analyze existing file
            if not os.path.exists(args.analyze_only):
                print(f"Error: Heaptrack file '{args.analyze_only}' not found!")
                sys.exit(1)
            
            print(f"Analyzing existing heaptrack file: {args.analyze_only}")
            success = analyze_heaptrack_data(args.analyze_only, container_name)
            
        else:
            # Full workflow: run Cobaya then analyze
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
