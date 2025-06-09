#!/usr/bin/env python3
"""
Simple test script to demonstrate memory profiling capabilities.
This script intentionally creates some memory allocations to test valgrind and heaptrack.
"""

import sys
import time

def create_memory_leak():
    """Create a simple memory leak for testing."""
    leaked_list = []
    for i in range(1000):
        # Create some data that won't be freed
        data = [j * i for j in range(100)]
        leaked_list.append(data)
    
    # Return only part of the data, "leaking" the rest
    return leaked_list[:10]

def normal_memory_usage():
    """Normal memory usage that should be properly freed."""
    temp_data = []
    for i in range(500):
        temp_data.append([j for j in range(50)])
    
    # Process the data
    result = sum(len(sublist) for sublist in temp_data)
    return result

def main():
    print("=== Simple Memory Test ===")
    print("This script demonstrates memory profiling with valgrind and heaptrack")
    
    print("\n1. Creating normal memory usage...")
    result1 = normal_memory_usage()
    print(f"   Normal usage result: {result1}")
    
    print("\n2. Creating intentional memory leak...")
    result2 = create_memory_leak()
    print(f"   Leak test result: {len(result2)} items returned")
    
    print("\n3. Doing some more allocations...")
    big_list = [i**2 for i in range(10000)]
    print(f"   Created list with {len(big_list)} items")
    
    print("\n4. Sleeping briefly to allow profilers to capture data...")
    time.sleep(1)
    
    print("\nTest completed!")
    print("\nTo run with memory profiling:")
    print("  valgrind --tool=memcheck --leak-check=full python simple-test.py")
    print("  heaptrack python simple-test.py")

if __name__ == "__main__":
    main()
