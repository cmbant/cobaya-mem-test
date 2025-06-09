#!/usr/bin/env python3
"""
Heaptrack Analysis Script

This script analyzes an existing heaptrack file and generates
a detailed report focusing on memory leaks, particularly from camblib.so

Usage: python analyze_heaptrack.py <heaptrack_file>
       uv run analyze_heaptrack.py <heaptrack_file>

Example: python analyze_heaptrack.py test_debug/heaptrack_test.gz.gz
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


def generate_memory_report(heaptrack_file, container_name, output_dir):
    """Generate detailed memory leak report focusing on actual leaks."""
    print("Generating memory leak report...")

    report_file = f"{output_dir}/memory_report.txt"

    # Start the report
    with open(report_file, 'w') as f:
        f.write("=== HEAPTRACK MEMORY LEAK ANALYSIS REPORT ===\n")
        f.write(f"Generated: {datetime.datetime.now()}\n")
        f.write(f"Heaptrack file: {heaptrack_file}\n")
        f.write("\n")

    # Generate different sections focusing on actual leaks
    sections = [
        ("SUMMARY STATISTICS", f"heaptrack_print -f {heaptrack_file} | tail -10"),
        ("ACTUAL MEMORY LEAKS - DETAILED", f"heaptrack_print -f {heaptrack_file} --print-leaks"),
        ("CAMBLIB.SO MEMORY LEAKS", f"heaptrack_print -f {heaptrack_file} --print-leaks | grep -A 15 -B 5 'camblib.so'"),
        ("SPECIFIC FUNCTIONS - results_MOD_Lsamples_init", f"heaptrack_print -f {heaptrack_file} --print-leaks | grep -A 15 -B 5 'results_MOD_Lsamples_init'"),
        ("SPECIFIC FUNCTIONS - results_MOD_init_cltransfer", f"heaptrack_print -f {heaptrack_file} --print-leaks | grep -A 15 -B 5 'results_MOD_init_cltransfer'"),
        ("LEAK SUMMARY BY SIZE", f"heaptrack_print -f {heaptrack_file} --print-leaks | grep -E '^[0-9]+.*leaked.*from' | head -20")
    ]

    for section_name, command in sections:
        print(f"  Generating {section_name.lower()}...")

        docker_cmd = f"""docker run --rm \
            -v "{os.getcwd()}:/workspace" \
            -w /workspace \
            {container_name} \
            bash -c "{command}" """

        try:
            result = run_command(docker_cmd)

            with open(report_file, 'a') as f:
                f.write(f"=== {section_name} ===\n")
                if result.stdout.strip():
                    f.write(result.stdout)
                else:
                    f.write("No data found for this section.\n")
                f.write("\n\n")

        except subprocess.CalledProcessError:
            with open(report_file, 'a') as f:
                f.write(f"=== {section_name} ===\n")
                f.write("Error generating this section.\n\n")

    print(f"Report saved to: {report_file}")
    return report_file


def display_key_findings(heaptrack_file, container_name):
    """Display key findings focusing on actual memory leaks."""
    print("\n=== KEY MEMORY LEAK FINDINGS ===\n")

    # Get overall statistics
    print("1. Overall Memory Statistics:")
    docker_cmd = f"""docker run --rm \
        -v "{os.getcwd()}:/workspace" \
        -w /workspace \
        {container_name} \
        bash -c "heaptrack_print -f {heaptrack_file} | tail -6" """

    try:
        result = run_command(docker_cmd)
        if result.stdout.strip():
            print(result.stdout)
        else:
            print("No data found.")
    except subprocess.CalledProcessError:
        print("Error retrieving data.")

    print()

    # Get actual leak summary
    print("2. Memory Leak Summary:")
    docker_cmd = f"""docker run --rm \
        -v "{os.getcwd()}:/workspace" \
        -w /workspace \
        {container_name} \
        bash -c "heaptrack_print -f {heaptrack_file} --print-leaks | grep -E '^[0-9]+.*leaked.*from' | head -10" """

    try:
        result = run_command(docker_cmd)
        if result.stdout.strip():
            print(result.stdout)
        else:
            print("No specific leak data found.")
    except subprocess.CalledProcessError:
        print("Error retrieving leak data.")

    print()

    # Check for specific problematic functions
    print("3. Specific Function Leaks:")

    functions_to_check = [
        "results_MOD_Lsamples_init",
        "results_MOD_init_cltransfer",
        "camblib.so"
    ]

    for func in functions_to_check:
        print(f"\n   Checking {func}:")
        docker_cmd = f"""docker run --rm \
            -v "{os.getcwd()}:/workspace" \
            -w /workspace \
            {container_name} \
            bash -c "heaptrack_print -f {heaptrack_file} --print-leaks | grep -A 3 -B 1 '{func}' | head -10" """

        try:
            result = run_command(docker_cmd)
            if result.stdout.strip():
                print(result.stdout)
            else:
                print(f"   No leaks found in {func}")
        except subprocess.CalledProcessError:
            print(f"   Error checking {func}")

    print()


def create_summary(output_dir, heaptrack_file):
    """Create a summary file with key findings."""
    summary_file = f"{output_dir}/summary.txt"
    
    with open(summary_file, 'w') as f:
        f.write("=== HEAPTRACK ANALYSIS SUMMARY ===\n")
        f.write(f"Generated: {datetime.datetime.now()}\n")
        f.write(f"Heaptrack data: {heaptrack_file}\n\n")
        
        f.write("Files created:\n")
        f.write("- memory_report.txt: Detailed heaptrack analysis\n")
        f.write("- summary.txt: This summary file\n\n")
        
        f.write("To view the full interactive analysis:\n")
        f.write(f"  heaptrack_gui {heaptrack_file}\n\n")
        
        f.write("To re-analyze the data:\n")
        f.write(f"  heaptrack_print {heaptrack_file}\n\n")
        
        f.write("Key areas to check in memory_report.txt:\n")
        f.write("1. Summary statistics for total memory usage\n")
        f.write("2. Top memory allocators to identify heavy users\n")
        f.write("3. Leaked memory locations for actual leaks\n")
        f.write("4. CAMBLIB.SO specific analysis for Fortran-related leaks\n")
    
    return summary_file


def main():
    parser = argparse.ArgumentParser(
        description="Analyze heaptrack data and generate memory leak reports"
    )
    parser.add_argument("heaptrack_file", help="Heaptrack data file (.gz)")
    parser.add_argument("--container", default="cobaya-memtest", 
                       help="Docker container name (default: cobaya-memtest)")
    
    args = parser.parse_args()
    
    heaptrack_file = args.heaptrack_file
    container_name = args.container
    
    # Check if heaptrack file exists
    if not os.path.exists(heaptrack_file):
        print(f"Error: Heaptrack file '{heaptrack_file}' not found!")
        sys.exit(1)
    
    # Check if Docker image exists
    if not check_docker_image(container_name):
        print(f"Error: Docker image '{container_name}' not found!")
        print(f"Please build it first with: docker build -t {container_name} .")
        sys.exit(1)
    
    # Create output directory
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"analysis_results_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    print("=== Heaptrack Memory Analysis ===")
    print(f"Input file: {heaptrack_file}")
    print(f"Output directory: {output_dir}")
    print(f"Timestamp: {timestamp}")
    print()
    
    try:
        # Step 1: Generate detailed report
        print("Step 1: Generating memory leak report...")
        report_file = generate_memory_report(heaptrack_file, container_name, output_dir)
        print(f"✓ Report saved to: {report_file}")
        
        # Step 2: Create summary
        print("\nStep 2: Creating summary...")
        summary_file = create_summary(output_dir, heaptrack_file)
        print(f"✓ Summary saved to: {summary_file}")
        
        # Step 3: Display key findings
        display_key_findings(heaptrack_file, container_name)
        
        print("=== MEMORY ANALYSIS COMPLETED ===")
        print(f"\nResults saved in: {output_dir}/")
        print("- memory_report.txt: Detailed analysis")
        print("- summary.txt: Summary and instructions")
        print(f"\nFor detailed analysis, see: {output_dir}/memory_report.txt")
        print(f"To view interactively: heaptrack_gui {heaptrack_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
