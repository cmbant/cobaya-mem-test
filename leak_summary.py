#!/usr/bin/env python3
"""
Memory Leak Summary Generator

This script creates a clean summary of memory leaks from heaptrack data,
focusing on actual leaks with sizes and function names.

Usage: python leak_summary.py <heaptrack_file>
       uv run leak_summary.py <heaptrack_file>
"""

import sys
import os
import subprocess
import datetime
import argparse
import re


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
        raise


def check_docker_image(container_name):
    """Check if Docker image exists."""
    try:
        run_command(f"docker image inspect {container_name}")
        return True
    except subprocess.CalledProcessError:
        return False


def extract_leak_summary(heaptrack_file, container_name):
    """Extract and parse memory leak information with stack traces."""
    print("Extracting memory leak data...")

    # Get the leak data
    docker_cmd = f"""docker run --rm \
        -v "{os.getcwd()}:/workspace" \
        -w /workspace \
        {container_name} \
        bash -c "heaptrack_print -f {heaptrack_file} --print-leaks" """

    result = run_command(docker_cmd)
    leak_data = result.stdout

    # Parse leak information with stack traces
    leaks = []
    lines = leak_data.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for leak lines like "12.47M leaked over 30 calls from"
        leak_match = re.match(r'^([0-9.]+[KMGT]?B?) leaked over ([0-9,]+) calls from$', line)
        if leak_match:
            size = leak_match.group(1)
            calls = leak_match.group(2).replace(',', '')

            # Extract the stack trace starting from the next line
            stack_trace = []
            is_camblib = False
            func_name = ""

            # Look ahead to collect the full stack trace
            j = i + 1
            while j < len(lines) and lines[j].strip():
                trace_line = lines[j].strip()
                stack_trace.append(trace_line)

                # The first non-empty line is the main function
                if not func_name and trace_line:
                    func_name = trace_line

                # Check if any line contains camblib.so
                if 'camblib.so' in trace_line:
                    is_camblib = True

                j += 1

            # Only add if we found a function name
            if func_name:
                leaks.append({
                    'size': size,
                    'calls': int(calls),
                    'function': func_name,
                    'is_camblib': is_camblib,
                    'stack_trace': stack_trace
                })

            # Move to the end of this leak's stack trace
            i = j
        else:
            i += 1

    return leaks


def convert_size_to_bytes(size_str):
    """Convert size string like '12.47M' to bytes for sorting."""
    if size_str.endswith('B'):
        size_str = size_str[:-1]

    multipliers = {'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}

    for suffix, multiplier in multipliers.items():
        if size_str.endswith(suffix):
            return float(size_str[:-1]) * multiplier

    return float(size_str)


def format_stack_trace(stack_trace, max_lines=10):
    """Format stack trace for display, limiting to most relevant lines."""
    if not stack_trace:
        return "No stack trace available"

    # Take the first few lines (most relevant) and last few lines if trace is long
    if len(stack_trace) <= max_lines:
        return '\n'.join(f"    {line}" for line in stack_trace)
    else:
        first_part = stack_trace[:max_lines//2]
        last_part = stack_trace[-(max_lines//2):]
        formatted_lines = []

        for line in first_part:
            formatted_lines.append(f"    {line}")

        formatted_lines.append("    ... (stack trace truncated) ...")

        for line in last_part:
            formatted_lines.append(f"    {line}")

        return '\n'.join(formatted_lines)


def generate_leak_summary(heaptrack_file, container_name):
    """Generate a clean summary of memory leaks."""
    
    # Get overall statistics
    docker_cmd = f"""docker run --rm \
        -v "{os.getcwd()}:/workspace" \
        -w /workspace \
        {container_name} \
        bash -c "heaptrack_print -f {heaptrack_file} | tail -6" """
    
    stats_result = run_command(docker_cmd)
    
    # Extract leak data
    leaks = extract_leak_summary(heaptrack_file, container_name)
    
    # Sort leaks by size (largest first)
    leaks.sort(key=lambda x: convert_size_to_bytes(x['size']), reverse=True)
    
    # Create summary
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = f"leak_summary_{timestamp}.txt"
    
    with open(summary_file, 'w') as f:
        f.write("=== MEMORY LEAK SUMMARY REPORT ===\n")
        f.write(f"Generated: {datetime.datetime.now()}\n")
        f.write(f"Heaptrack file: {heaptrack_file}\n")
        f.write("\n")
        
        f.write("=== OVERALL STATISTICS ===\n")
        f.write(stats_result.stdout)
        f.write("\n")
        
        f.write("=== TOP MEMORY LEAKS (by size) ===\n")
        f.write(f"{'Size':<12} {'Calls':<8} {'Function':<50} {'CAMB?':<6}\n")
        f.write("-" * 80 + "\n")

        # Show top 20 leaks
        for leak in leaks[:20]:
            camb_indicator = "YES" if leak['is_camblib'] else "NO"
            f.write(f"{leak['size']:<12} {leak['calls']:<8} {leak['function']:<50} {camb_indicator:<6}\n")

        f.write("\n")

        # Add detailed stack traces for top 5 leaks
        f.write("=== DETAILED STACK TRACES FOR TOP 5 LEAKS ===\n")
        f.write("This section shows the complete call stack for the largest memory leaks.\n\n")

        for i, leak in enumerate(leaks[:5], 1):
            f.write(f"#{i} LEAK: {leak['size']} leaked over {leak['calls']} calls\n")
            f.write(f"Main Function: {leak['function']}\n")
            f.write(f"CAMBLIB.SO: {'YES' if leak['is_camblib'] else 'NO'}\n")
            f.write("Stack Trace:\n")
            f.write(format_stack_trace(leak.get('stack_trace', []), max_lines=15))
            f.write("\n")
            f.write("-" * 80 + "\n\n")
        
        # Separate CAMB-specific leaks
        camblib_leaks = [leak for leak in leaks if leak['is_camblib']]
        if camblib_leaks:
            f.write("=== CAMBLIB.SO SPECIFIC LEAKS ===\n")
            f.write(f"{'Size':<12} {'Calls':<8} {'Function':<50}\n")
            f.write("-" * 70 + "\n")
            
            for leak in camblib_leaks:
                f.write(f"{leak['size']:<12} {leak['calls']:<8} {leak['function']:<50}\n")
            
            f.write("\n")
            
            # Calculate total CAMB leaks
            total_camb_size = sum(convert_size_to_bytes(leak['size']) for leak in camblib_leaks)
            total_camb_calls = sum(leak['calls'] for leak in camblib_leaks)
            
            f.write(f"TOTAL CAMBLIB.SO LEAKS: {len(camblib_leaks)} different functions\n")
            f.write(f"TOTAL CAMBLIB.SO LEAKED MEMORY: ~{total_camb_size/1024/1024:.1f}M\n")
            f.write(f"TOTAL CAMBLIB.SO LEAKED CALLS: {total_camb_calls:,}\n")
        
        f.write("\n")
        f.write("=== SPECIFIC FUNCTIONS OF INTEREST ===\n")

        # Look for specific functions mentioned
        specific_functions = [
            "results_MOD_Lsamples_init",
            "results_MOD_init_cltransfer",
            "spherbessels_MOD_initspherbessels",
            "config_MOD_checkloadedhighltemplate"
        ]

        for func_name in specific_functions:
            matching_leaks = [leak for leak in leaks if func_name.lower() in leak['function'].lower()]
            if matching_leaks:
                f.write(f"\n{func_name}:\n")
                for j, leak in enumerate(matching_leaks):
                    f.write(f"  Leak #{j+1}: {leak['size']} leaked over {leak['calls']} calls\n")
                    f.write(f"  Function: {leak['function']}\n")
                    if leak.get('stack_trace'):
                        f.write("  Stack Trace:\n")
                        f.write(format_stack_trace(leak['stack_trace'], max_lines=8))
                        f.write("\n")
                    f.write("  " + "-" * 60 + "\n")
            else:
                f.write(f"\n{func_name}: No leaks found\n")
    
    return summary_file, leaks


def main():
    parser = argparse.ArgumentParser(
        description="Generate clean memory leak summary from heaptrack data"
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
    
    print("=== Memory Leak Summary Generator ===")
    print(f"Input file: {heaptrack_file}")
    print()
    
    try:
        summary_file, leaks = generate_leak_summary(heaptrack_file, container_name)
        
        print(f"✓ Summary saved to: {summary_file}")
        print()
        
        # Display key findings
        print("=== KEY FINDINGS ===")

        # Top 5 leaks
        print("\nTop 5 Memory Leaks:")
        for i, leak in enumerate(leaks[:5]):
            camb_indicator = " (CAMBLIB.SO)" if leak['is_camblib'] else ""
            print(f"  {i+1}. {leak['size']} - {leak['function']}{camb_indicator}")

        # Show detailed stack trace for the top leak
        if leaks:
            top_leak = leaks[0]
            print(f"\n=== TOP LEAK STACK TRACE ===")
            print(f"Leak: {top_leak['size']} leaked over {top_leak['calls']} calls")
            print(f"Function: {top_leak['function']}")
            print(f"CAMBLIB.SO: {'YES' if top_leak['is_camblib'] else 'NO'}")
            print("Stack Trace:")
            if top_leak.get('stack_trace'):
                # Show first 8 lines of stack trace in console
                stack_lines = top_leak['stack_trace'][:8]
                for line in stack_lines:
                    print(f"  {line}")
                if len(top_leak['stack_trace']) > 8:
                    print(f"  ... ({len(top_leak['stack_trace']) - 8} more lines in detailed report)")
            else:
                print("  No stack trace available")

        # CAMB-specific summary
        camblib_leaks = [leak for leak in leaks if leak['is_camblib']]
        if camblib_leaks:
            total_camb_size = sum(convert_size_to_bytes(leak['size']) for leak in camblib_leaks)
            print(f"\nCAMBLIB.SO Summary:")
            print(f"  - {len(camblib_leaks)} different functions with leaks")
            print(f"  - ~{total_camb_size/1024/1024:.1f}M total leaked memory")
            print(f"  - Top CAMB leak: {camblib_leaks[0]['size']} from {camblib_leaks[0]['function']}")

        print(f"\nFor detailed analysis, see: {summary_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
