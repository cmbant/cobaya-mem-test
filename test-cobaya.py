#!/usr/bin/env python3
"""
Simple test script to verify Cobaya installation and run a quick test.
This script can be used to test memory profiling tools.
"""

import sys
import os
import tempfile
import yaml

def test_cobaya_import():
    """Test that cobaya can be imported successfully."""
    try:
        import cobaya
        print(f"✓ Cobaya imported successfully (version {cobaya.__version__})")
        return True
    except ImportError as e:
        print(f"✗ Failed to import cobaya: {e}")
        return False

def test_dependencies():
    """Test that key dependencies are available."""
    dependencies = {
        'numpy': 'numpy',
        'scipy': 'scipy', 
        'matplotlib': 'matplotlib',
        'camb': 'camb',
        'mpi4py': 'mpi4py'
    }
    
    success = True
    for name, module in dependencies.items():
        try:
            __import__(module)
            print(f"✓ {name} available")
        except ImportError:
            print(f"✗ {name} not available")
            success = False
    
    return success

def create_minimal_test_yaml():
    """Create a minimal test configuration for quick testing."""
    test_config = {
        'theory': {
            'camb': {
                'use_renames': True,
                'extra_args': {
                    'num_massive_neutrinos': 0,
                    'nnu': 3.044
                }
            }
        },
        'params': {
            'H0': {'prior': {'min': 60, 'max': 80}, 'ref': 70, 'proposal': 1},
            'ombh2': {'prior': {'min': 0.02, 'max': 0.025}, 'ref': 0.022, 'proposal': 0.0001},
            'omch2': {'prior': {'min': 0.1, 'max': 0.15}, 'ref': 0.12, 'proposal': 0.001}
        },
        'sampler': {
            'evaluate': {'N': 1}  # Just evaluate once for testing
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_config, f)
        return f.name

def test_cobaya_run():
    """Test that cobaya can run a simple evaluation."""
    try:
        from cobaya.run import run
        
        # Create minimal test config
        test_file = create_minimal_test_yaml()
        print(f"Created test config: {test_file}")
        
        # Run cobaya
        print("Running minimal cobaya test...")
        info = yaml.safe_load(open(test_file))
        updated_info, sampler = run(info)
        
        print("✓ Cobaya run completed successfully")
        
        # Clean up
        os.unlink(test_file)
        return True
        
    except Exception as e:
        print(f"✗ Cobaya run failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=== Cobaya Installation Test ===\n")
    
    tests = [
        ("Import test", test_cobaya_import),
        ("Dependencies test", test_dependencies),
        ("Run test", test_cobaya_run)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        result = test_func()
        results.append(result)
    
    print(f"\n=== Test Summary ===")
    all_passed = all(results)
    status = "PASSED" if all_passed else "FAILED"
    print(f"Overall status: {status}")
    
    if all_passed:
        print("\n🎉 All tests passed! Cobaya is ready for memory leak testing.")
        print("\nMemory profiling examples:")
        print("  valgrind --tool=memcheck --leak-check=full python test-cobaya.py")
        print("  heaptrack python test-cobaya.py")
    else:
        print("\n❌ Some tests failed. Please check the installation.")
        sys.exit(1)

if __name__ == "__main__":
    main()
