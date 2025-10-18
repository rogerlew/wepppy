"""
Test type hints for wepppy.nodb.core.climate module.

This test validates that type hints have been properly added to the climate module
and can be introspected at runtime.
"""
import ast
import inspect
from pathlib import Path


def test_climate_module_has_type_hints():
    """Validate that climate.py has comprehensive type hints."""
    climate_path = Path(__file__).parent.parent.parent / 'wepppy' / 'nodb' / 'core' / 'climate.py'
    
    assert climate_path.exists(), f"climate.py not found at {climate_path}"
    
    with open(climate_path) as f:
        code = f.read()
    
    # Parse the module
    tree = ast.parse(code)
    
    # Count functions with type hints
    funcs_with_hints = 0
    total_funcs = 0
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            total_funcs += 1
            # Check if function has return type hint or parameter type hints
            if node.returns is not None or any(arg.annotation for arg in node.args.args):
                funcs_with_hints += 1
    
    # All functions should have type hints
    assert funcs_with_hints == total_funcs, \
        f"Only {funcs_with_hints}/{total_funcs} functions have type hints"
    
    assert total_funcs >= 100, \
        f"Expected at least 100 functions, found {total_funcs}"
    
    print(f"✓ All {total_funcs} functions have type hints")


def test_climate_module_imports():
    """Validate that key climate module exports can be imported."""
    # This test may fail if dependencies are not installed, so we'll just
    # verify the module file compiles without syntax errors
    climate_path = Path(__file__).parent.parent.parent / 'wepppy' / 'nodb' / 'core' / 'climate.py'
    
    with open(climate_path) as f:
        code = f.read()
    
    # This will raise SyntaxError if there are syntax issues
    compile(code, str(climate_path), 'exec')
    
    print("✓ climate.py compiles without syntax errors")


def test_climate_helper_functions_typed():
    """Validate that helper functions have type hints."""
    climate_path = Path(__file__).parent.parent.parent / 'wepppy' / 'nodb' / 'core' / 'climate.py'
    
    with open(climate_path) as f:
        code = f.read()
    
    tree = ast.parse(code)
    
    # Find specific helper functions and check they have type hints
    helper_functions = [
        'lng_lat_to_pixel_center',
        'daymet_pixel_center',
        'gridmet_pixel_center',
        'prism4k_pixel_center',
        'nexrad_pixel_center',
        'download_file',
        'breakpoint_file_fix',
        'get_monthlies',
        'get_prism_p_annual_monthlies',
        'get_daymet_p_annual_monthlies',
        'get_gridmet_p_annual_monthlies',
    ]
    
    found_functions = {}
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in helper_functions:
            has_return_type = node.returns is not None
            has_param_types = any(arg.annotation for arg in node.args.args)
            found_functions[node.name] = {
                'has_return_type': has_return_type,
                'has_param_types': has_param_types
            }
    
    for func_name in helper_functions:
        assert func_name in found_functions, f"Function {func_name} not found"
        func_info = found_functions[func_name]
        assert func_info['has_return_type'], f"Function {func_name} missing return type hint"
        assert func_info['has_param_types'], f"Function {func_name} missing parameter type hints"
    
    print(f"✓ All {len(helper_functions)} helper functions have comprehensive type hints")


def test_climate_class_has_init_typed():
    """Validate that Climate.__init__ has type hints."""
    climate_path = Path(__file__).parent.parent.parent / 'wepppy' / 'nodb' / 'core' / 'climate.py'
    
    with open(climate_path) as f:
        code = f.read()
    
    tree = ast.parse(code)
    
    # Find Climate class
    climate_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'Climate':
            climate_class = node
            break
    
    assert climate_class is not None, "Climate class not found"
    
    # Find __init__ method
    init_method = None
    for item in climate_class.body:
        if isinstance(item, ast.FunctionDef) and item.name == '__init__':
            init_method = item
            break
    
    assert init_method is not None, "Climate.__init__ not found"
    
    # Check return type (should be -> None)
    assert init_method.returns is not None, "Climate.__init__ missing return type hint"
    
    # Check parameter types (excluding self)
    params_with_annotations = [arg for arg in init_method.args.args[1:] if arg.annotation]
    total_params = len(init_method.args.args) - 1  # Exclude self
    
    assert len(params_with_annotations) == total_params, \
        f"Only {len(params_with_annotations)}/{total_params} parameters have type hints in Climate.__init__"
    
    print(f"✓ Climate.__init__ has comprehensive type hints ({total_params} parameters)")


if __name__ == '__main__':
    test_climate_module_has_type_hints()
    test_climate_module_imports()
    test_climate_helper_functions_typed()
    test_climate_class_has_init_typed()
    print("\n✅ All climate type hint tests passed!")
