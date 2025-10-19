# Contributing Guide for AI Coding Agents

> Specialized guide for Copilot, Claude, Gemini, and other AI coding assistants working on WEPPpy

## Quick Start for Agents

### 1. Understanding the Codebase
Before making changes, consult these documents in order:
1. **ARCHITECTURE.md** ⭐ - System design and component interactions
2. **AGENTS.md** ⭐⭐⭐ - Agent-specific coding patterns and conventions (START HERE)
3. **API_REFERENCE.md** ⭐⭐ - Quick reference for common APIs
4. **readme.md** ⭐ - User-facing documentation

**For quick fixes**: Jump to relevant section in this doc  
**For new features**: Read ARCHITECTURE.md first  
**For refactoring**: Review AGENTS.md patterns

### 2. Key Principles
- **Preserve existing patterns** - Match the style of surrounding code
- **Minimal changes** - Edit only what's necessary
- **Backward compatibility** - Don't break `.nodb` serialization
- **Test coverage** - Add tests for new functionality
- **Documentation** - Update docstrings and README files

### 3. Before You Code
```bash
# 1. Find similar implementations
git grep -n "similar_function_name"

# 2. Check test patterns
ls tests/**/test_*.py | grep relevant_module

# 3. Understand dependencies
grep -r "from.*import" wepppy/module_name/ | sort -u
```

## Decision Trees for Common Tasks

### "Where should my code go?"

```
Need to add functionality?
│
├─ Modifying run data/state?
│  └─ Add to relevant NoDb controller (Wepp, Climate, Watershed, etc.)
│
├─ Background processing task?
│  └─ Create RQ job in wepppy/rq/
│
├─ HTTP endpoint?
│  ├─ MCP query engine? → wepppy/query_engine/app/routes/
│  └─ Main Flask app? → wepppy/weppcloud/routes/
│
├─ Data analysis/query?
│  └─ wepppy/query_engine/ (DuckDB queries)
│
├─ File format conversion?
│  └─ wepppy/export/ or wepppy/climates/
│
└─ Utility function?
   └─ wepppy/all_your_base.py (if general) or relevant module
```

### "How should I test this?"

```
What are you testing?
│
├─ NoDb controller?
│  └─ Unit test: tests/nodb/test_<controller>.py
│     • Test initialization
│     • Test serialization
│     • Test locking
│     • Test state transitions
│
├─ RQ background job?
│  └─ Integration test: tests/rq/test_jobs.py
│     • Mock Redis if possible
│     • Test job queuing
│     • Test job execution
│     • Test error handling
│
├─ Flask route?
│  └─ Route test: tests/weppcloud/test_routes.py
│     • Use Flask test client
│     • Test all HTTP methods
│     • Test auth requirements
│     • Test error responses
│
├─ Query engine?
│  └─ Query test: tests/query_engine/test_queries.py
│     • Test SQL generation
│     • Test result formatting
│     • Test query validation
│
└─ Utility function?
   └─ Unit test: tests/test_utils.py
      • Test happy path
      • Test edge cases
      • Test error conditions
```

### American English Normalization
- Run `uk2us` on touched files to translate British spellings to American spellings.
  - Single file: `uk2us -i path/to/file.py`
  - Batch example: `find wepppy -type f -name '*.py' -print0 | xargs -0 uk2us -i`
- Agents have write access to `/workdir/uk2us/config/uk2us_rules.json` to correct odd replacements.
  - Add to `skip_replacements` to block a mapping.
  - Add to `forced_mappings` to pin a specific substitution.
  - After adjusting the config, rerun `uk2us` to confirm the changes.

## Code Organization Patterns

### Module Structure

Every Python module should have:

1. **Header comments** (copyright, attribution)
2. **Imports** (standard lib → third-party → local)
3. **`__all__`** (explicit public API)
4. **Module docstring** (purpose, key classes/functions)
5. **Implementation**

```python
# Copyright (c) 2016-2025, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)

"""Module for [specific purpose].

This module provides:
- [Key functionality 1]
- [Key functionality 2]

Example:
    >>> from wepppy.module import MyClass
    >>> obj = MyClass()
    >>> obj.do_something()
"""

# Standard library
import os
from pathlib import Path
from typing import Optional, List, Dict

# Third-party
import numpy as np
import pandas as pd

# Local
from wepppy.nodb.base import NoDbBase
from wepppy.all_your_base import isfloat

__all__ = [
    'MyClass',
    'MyException',
    'helper_function',
]

class MyClass(NoDbBase):
    """One-line summary.
    
    Longer description explaining the purpose and usage.
    
    Attributes:
        attr1: Description of attribute 1
        attr2: Description of attribute 2
    
    Example:
        >>> obj = MyClass.getInstance(wd)
        >>> obj.do_something()
    """
    
    def __init__(self, wd: str):
        """Initialize instance.
        
        Args:
            wd: Working directory path
        """
        super().__init__(wd)
        self.attr1 = None
    
    def do_something(self, param: str) -> bool:
        """Do something with parameter.
        
        Args:
            param: Description of parameter
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValueError: If param is invalid
            
        Example:
            >>> result = obj.do_something('value')
            >>> assert result is True
        """
        pass
```

### Managing `__all__` Exports

Always update `__all__` when:
- ✓ Adding new public classes
- ✓ Adding new public functions  
- ✓ Adding new exceptions

Never add to `__all__`:
- ✗ Private functions (prefixed with `_`)
- ✗ Helper functions meant for internal use only
- ✗ Imported dependencies

Example:

```python
__all__ = [
    # Classes (alphabetical)
    'MyClass',
    'MyOtherClass',
    # Exceptions
    'MyException',
    'MyOtherException',
    # Functions (alphabetical)
    'helper_function',
    'utility_function',
]
```

### Type Hints

Add type hints to **all new code** and **refactored code**:

```python
from typing import Optional, List, Dict, Tuple, Union, Callable
from pathlib import Path

# Function signatures
def process_data(
    input_path: Path,
    options: Optional[Dict[str, str]] = None
) -> Tuple[bool, str]:
    """Process data from file.
    
    Args:
        input_path: Path to input file
        options: Optional processing options
        
    Returns:
        Tuple of (success, message)
    """
    pass

# Class attributes
class MyController(NoDbBase):
    """Controller with typed attributes."""
    
    data: Dict[str, float]
    records: List[Dict]
    config_path: Optional[Path]
    
    def __init__(self, wd: str):
        super().__init__(wd)
        self.data = {}
        self.records = []
        self.config_path = None
```

### Common WEPPpy Type Patterns

```python
# File paths (prefer Path over str)
from pathlib import Path
from typing import Union

PathLike = Union[str, Path]

def load_config(path: PathLike) -> Dict[str, any]:
    """Load configuration from file."""
    path = Path(path)
    ...

# NoDb working directories (always str)
def process_run(wd: str) -> None:
    """Process run in working directory.
    
    Args:
        wd: Working directory path (must be str for NoDb)
    """
    ...

# Optional with None default
def analyze(
    data: List[float],
    threshold: Optional[float] = None
) -> Dict[str, float]:
    """Analyze data with optional threshold."""
    if threshold is None:
        threshold = 0.0
    ...

# Multiple return types
def parse_value(s: str) -> Union[int, float, str]:
    """Parse string to appropriate type."""
    ...

# Type aliases for complex structures
RunMetadata = Dict[str, Union[str, int, float, List[str]]]

def get_metadata(runid: str) -> RunMetadata:
    """Retrieve run metadata."""
    ...
```

### Docstring Format

Use **Google-style docstrings** for consistency:

```python
def complex_function(
    param1: str,
    param2: int,
    optional_param: Optional[bool] = None
) -> Dict[str, any]:
    """One-line summary of what function does.
    
    Longer description explaining behavior, side effects,
    and important implementation details.
    
    Args:
        param1: Description of first parameter
        param2: Description of second parameter
        optional_param: Description of optional parameter.
            Defaults to None.
    
    Returns:
        Dictionary containing:
            - 'key1': Description of value 1
            - 'key2': Description of value 2
    
    Raises:
        ValueError: When param1 is empty
        IOError: When file cannot be read
    
    Example:
        >>> result = complex_function('test', 42)
        >>> print(result['key1'])
        'value1'
        
    Note:
        Important implementation notes or caveats.
        
    Warning:
        Warnings about dangerous usage patterns.
    """
    pass
```

### Extended Docstring Patterns

```python
# When to document private methods
class MyController:
    def _internal_helper(self, data: List[int]) -> bool:
        """Internal helper for data validation.
        
        Note:
            This is a private method and should not be called directly.
            Use public API methods instead.
        """
        ...

# Documenting complex return types
def analyze_watershed() -> Dict[str, any]:
    """Analyze watershed characteristics.
    
    Returns:
        Dictionary with structure::
        
            {
                'area_km2': float,
                'channels': [
                    {
                        'id': int,
                        'length_m': float,
                        'slope_pct': float
                    },
                    ...
                ],
                'metadata': {
                    'version': str,
                    'timestamp': str
                }
            }
    """
    ...

# Documenting side effects
def generate_climate_data(wd: str) -> None:
    """Generate climate input files.
    
    Side Effects:
        - Creates climate/ directory in wd
        - Writes multiple .cli files
        - Updates run state in Redis
        - Logs progress to wepppy.log
    
    Warning:
        Overwrites existing climate files without backup.
    """
    ...
```

## Logging Patterns

### When to Log

```python
import logging
from wepppy.all_your_base import get_logger

log = get_logger(__name__)

# Log at appropriate levels
log.debug('Detailed diagnostic info')  # Development only
log.info('Normal operation milestone')  # User-visible progress
log.warning('Recoverable issue')        # Something unexpected but handled
log.error('Operation failed')           # Error that prevents completion
log.critical('System-level failure')    # Requires immediate attention

# Good logging examples
class MyController:
    def process(self):
        """Process run data."""
        log.info(f'Starting processing for run {self.run_id}')
        
        try:
            self._validate_inputs()
            log.debug(f'Inputs validated: {len(self.inputs)} items')
            
            results = self._compute()
            log.info(f'Processing complete: {len(results)} results')
            
            return results
            
        except ValueError as e:
            log.error(f'Validation failed: {e}')
            raise
        except Exception as e:
            log.critical(f'Unexpected error in processing: {e}', exc_info=True)
            raise
```

### Don't Over-Log

```python
# WRONG - too noisy
for item in items:
    log.debug(f'Processing item {item}')  # Logs every item!
    
# CORRECT - log summary
log.debug(f'Processing {len(items)} items')
# ... process items ...
log.debug(f'Completed processing {len(results)} items')
```

## NoDb Controller Patterns

### Creating New Controllers

```python
"""New NoDb controller module.

Provides [functionality description].
"""

from wepppy.nodb.base import NoDbBase

__all__ = [
    'MyController',
    'MyControllerNoDbLockedException',
]

class MyControllerNoDbLockedException(Exception):
    """Raised when MyController is already locked."""
    pass

class MyController(NoDbBase):
    """Manages [specific functionality].
    
    This controller handles [detailed description].
    
    Attributes:
        data: Description of data attribute
        config: Configuration dictionary
    
    Example:
        >>> controller = MyController.getInstance(wd)
        >>> with controller.locked():
        ...     controller.data['key'] = 'value'
        ...     controller.dump_and_unlock()
    """
    
    def __init__(self, wd: str, cfg_fn: str = 'config.ini'):
        """Initialize controller.
        
        Args:
            wd: Working directory path
            cfg_fn: Configuration file name
        """
        super().__init__(wd, cfg_fn)
        
        self.data = {}
        self.config = {}
        
        self._lock_exception = MyControllerNoDbLockedException
    
    def my_method(self, param: str) -> None:
        """Method that modifies state.
        
        Args:
            param: Description
        """
        with self.locked():
            self.data[param] = 'value'
            self._logger.info(f"Updated {param}")
            self.dump_and_unlock()
```

### State Management in NoDb Controllers

```python
# Reading state (no lock needed)
def get_summary(self) -> Dict[str, any]:
    """Get summary without modifying state."""
    return {
        'status': self.status,
        'progress': self.progress
    }

# Mutating state (lock required)
def update_progress(self, value: float) -> None:
    """Update progress value.
    
    Note:
        Acquires lock automatically. Use context manager
        for multiple updates in a transaction.
    """
    with self.locked():
        self.progress = value
        self.dump_and_unlock()

# Bulk mutations (single lock)
def initialize_run(self, config: Dict) -> None:
    """Initialize run with configuration.
    
    Tip:
        Group related mutations in a single lock context
        for better performance and atomicity.
    """
    with self.locked():
        self.config = config
        self.status = 'initialized'
        self.progress = 0.0
        self.timestamp = datetime.now().isoformat()
        self.dump_and_unlock()

# Conditional mutations
def try_update(self, new_value: any) -> bool:
    """Attempt to update value.
    
    Returns:
        True if update succeeded, False if preconditions not met.
    """
    with self.locked():
        if self._can_update():
            self.value = new_value
            self.dump_and_unlock()
            return True
        else:
            self.unlock()  # Release without dumping
            return False
```

### Adding Methods to Existing Controllers

1. **Check existing patterns** in the controller
2. **Follow locking conventions** for mutations
3. **Add logging** for observable operations
4. **Update `__all__`** if adding public API

```python
# In wepppy/nodb/core/wepp.py

# ...existing code...

def new_analysis_method(self) -> Dict[str, float]:
    """Compute new analysis metric.
    
    Returns:
        Dictionary of metric names to values
        
    Example:
        >>> wepp = Wepp.getInstance(wd)
        >>> metrics = wepp.new_analysis_method()
        >>> print(metrics['avg_runoff'])
    """
    # Read-only operations don't need lock
    results = {}
    
    for hillslope_id in self.hillslope_ids:
        data = self._load_hillslope_output(hillslope_id)
        results[hillslope_id] = self._compute_metric(data)
    
    return results

# ...existing code...
```

## Testing Patterns

### NoDb Controller Tests

```python
"""Tests for MyController."""

import pytest
from pathlib import Path
from wepppy.nodb import MyController

def test_mycontroller_initialization(tmp_path):
    """Test controller initialization."""
    wd = str(tmp_path)
    controller = MyController.getInstance(wd)
    
    assert controller.wd == wd
    assert controller.data == {}

def test_mycontroller_serialization(tmp_path):
    """Test state persistence."""
    wd = str(tmp_path)
    
    # First instance
    controller1 = MyController.getInstance(wd)
    with controller1.locked():
        controller1.data['key'] = 'value'
        controller1.dump_and_unlock()
    
    # Verify singleton
    controller2 = MyController.getInstance(wd)
    assert controller1 is controller2
    assert controller2.data['key'] == 'value'
    
    # Clear cache and reload from disk
    MyController._instances.clear()
    controller3 = MyController.getInstance(wd)
    assert controller3.data['key'] == 'value'

def test_mycontroller_locking(tmp_path):
    """Test distributed locking."""
    wd = str(tmp_path)
    controller = MyController.getInstance(wd)
    
    with controller.locked():
        # Should not raise
        pass
    
    # Lock should be released
    with controller.locked():
        pass
```

### Test Coverage Guidelines

**Minimum coverage for new code:**
- Public methods: 100% coverage required
- Private methods: Coverage encouraged but not required
- Error paths: Must test at least one failure case

**What to test:**
- ✓ Happy path (normal operation)
- ✓ Edge cases (empty lists, None values, boundary conditions)
- ✓ Error cases (invalid input, missing files, lock conflicts)
- ✓ State transitions (initialization → processing → completion)
- ✓ Serialization roundtrip (save → load → verify)

**Example: Comprehensive controller tests:**

```python
def test_controller_lifecycle(tmp_path):
    """Test complete controller lifecycle."""
    # Creation
    controller = MyController.getInstance(str(tmp_path))
    assert controller.status == 'new'
    
    # Configuration
    with controller.locked():
        controller.config = {'key': 'value'}
        controller.dump_and_unlock()
    
    # Processing
    controller.process()
    assert controller.status == 'processing'
    
    # Completion
    controller.finalize()
    assert controller.status == 'complete'
    
    # Persistence
    controller2 = MyController.getInstance(str(tmp_path))
    assert controller2.status == 'complete'
    assert controller2.config['key'] == 'value'

def test_controller_error_handling(tmp_path):
    """Test error scenarios."""
    controller = MyController.getInstance(str(tmp_path))
    
    # Test invalid input
    with pytest.raises(ValueError, match="Invalid configuration"):
        controller.configure(None)
    
    # Test missing dependency
    with pytest.raises(FileNotFoundError):
        controller.process_missing_file()
    
    # Test lock conflict
    controller.lock()
    with pytest.raises(MyControllerNoDbLockedException):
        with controller.locked():
            pass
```

### Integration Tests

```python
"""Integration test for full workflow."""

import pytest
from wepppy.nodb import RedisPrep, Wepp, Climate, Watershed

@pytest.mark.integration
def test_full_simulation_workflow(tmp_path):
    """Test complete simulation from setup to results."""
    # Setup
    runid = 'test-run'
    wd = RedisPrep.create_working_directory(
        runid, base_dir=str(tmp_path)
    )
    
    # Configure
    climate = Climate.getInstance(wd)
    climate.mode = ClimateMode.CLIGEN
    climate.download_climate_data('14826')
    
    watershed = Watershed.getInstance(wd)
    watershed.outlet = Outlet(lat=46.8, lng=-116.8)
    watershed.abstract_watershed()
    
    wepp = Wepp.getInstance(wd)
    wepp.prep_hillslopes()
    wepp.run_hillslopes()
    wepp.run_watershed()
    
    # Verify results
    assert wepp.avg_soil_loss_tha > 0
    assert len(wepp.run_results) > 0
```

## Flask Route Patterns

### Adding New Routes

```python
"""New route blueprint module."""

from flask import Blueprint, jsonify, request
from wepppy.nodb.core import MyController
from os.path import join as _join

bp = Blueprint('my_routes', __name__, url_prefix='/my-feature')

@bp.route('/<runid>/action', methods=['POST'])
def perform_action(runid: str):
    """Perform action on run.
    
    Args:
        runid: Run identifier from URL
        
    Returns:
        JSON response with status
        
    Request Body:
        {
            "param1": "value1",
            "param2": 42
        }
        
    Response:
        {
            "success": true,
            "data": {...}
        }
    """
    try:
        # Validate request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        if 'param1' not in data:
            return jsonify({'error': 'Missing required parameter'}), 400
        
        # Get controller
        wd = _join('/geodata/weppcloud_runs', runid)
        controller = MyController.getInstance(wd)
        
        # Perform action
        with controller.locked():
            result = controller.perform_action(data['param1'])
            controller.dump_and_unlock()
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except FileNotFoundError:
        return jsonify({'error': 'Run not found'}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500
```

## Background Job Patterns

### Creating RQ Tasks

```python
"""Background task module."""

import time
from datetime import datetime
from wepppy.rq import job
from os.path import join as _join

@job('default', timeout=3600)
def my_background_task(
    runid: str,
    param1: str,
    param2: Optional[int] = None
) -> dict:
    """Execute background task for run.
    
    Args:
        runid: Run identifier (required first parameter)
        param1: Task-specific parameter
        param2: Optional parameter
        
    Returns:
        Dictionary with results:
            - 'success': Boolean indicating completion
            - 'data': Task output data
            - 'metrics': Performance metrics
    
    Example:
        >>> from wepppy.rq.my_tasks import my_background_task
        >>> job = my_background_task.delay('copacetic-note', 'value1')
        >>> result = job.result  # Blocks until complete
    """
    from wepppy.nodb.core import MyController
    
    start_time = time.time()
    
    # Build working directory path
    wd = _join('/geodata/weppcloud_runs', runid)
    
    # Get controller
    controller = MyController.getInstance(wd)
    
    # Acquire lock for thread-safe operations
    with controller.locked():
        controller._logger.info(
            f"Starting task with {param1}",
            extra={'task': 'my_background_task', 'param1': param1}
        )
        
        # Perform work
        result = controller.process(param1, param2)
        
        # Update state
        controller.last_run_time = time.time()
        
        # Persist changes
        controller.dump_and_unlock()
        
        controller._logger.info("Task completed successfully")
    
    return {
        'success': True,
        'data': result,
        'metrics': {
            'duration_s': time.time() - start_time
        }
    }
```

## Query Engine Patterns

### Adding New Query Presets

```python
# In wepppy/query_engine/app/query_presets.py

QUERY_PRESETS = {
    'my_analysis': {
        'name': 'My Analysis',
        'description': 'Compute [metric] for [entity]',
        'category': 'analysis',
        'payload': {
            'datasets': [
                {
                    'path': 'datasets/hillslopes.parquet',
                    'alias': 'h'
                }
            ],
            'columns': ['wepp_id', 'soil_loss'],
            'filters': [
                {
                    'column': 'soil_loss',
                    'operator': '>',
                    'value': 10.0
                }
            ],
            'aggregations': [
                {
                    'fn': 'AVG',
                    'column': 'soil_loss',
                    'alias': 'avg_loss'
                }
            ],
            'limit': 100
        }
    }
}
```

## Documentation Patterns

### Module Documentation

Every module needs:

```python
"""Module one-line description.

Longer description explaining:
- Purpose and scope
- Key components
- Usage examples
- Integration points

Example:
    >>> from wepppy.my_module import MyClass
    >>> obj = MyClass()
    >>> obj.method()

See Also:
    - Related module 1
    - Related module 2
    
Note:
    Important notes about module behavior.
"""
```

### Class Documentation

```python
class MyClass:
    """One-line class description.
    
    Longer description of class purpose, behavior,
    and important implementation details.
    
    Attributes:
        attr1: Type and description of attribute 1
        attr2: Type and description of attribute 2
    
    Example:
        >>> obj = MyClass(param1='value')
        >>> result = obj.method()
        >>> print(result)
        
    Note:
        Important usage notes.
        
    Warning:
        Pitfalls or dangerous patterns to avoid.
    """
```

### Method Documentation

```python
def method(
    self,
    param1: str,
    param2: Optional[int] = None
) -> Dict[str, any]:
    """One-line method description.
    
    Detailed explanation of what method does,
    including side effects and state changes.
    
    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2.
            Defaults to None.
    
    Returns:
        Dictionary containing:
            - 'key1': Description
            - 'key2': Description
    
    Raises:
        ValueError: When param1 is invalid
        RuntimeError: When operation fails
    
    Example:
        >>> result = obj.method('test')
        >>> assert 'key1' in result
        
    Note:
        Important implementation notes.
    """
```

## Git Workflow

### Commit Messages

Follow these conventions:

```bash
# Format: <type>: <subject>

# Types:
# - feat: New feature
# - fix: Bug fix
# - docs: Documentation only
# - refactor: Code restructuring
# - test: Adding tests
# - chore: Maintenance

# Good examples:
git commit -m "feat: Add phosphorus modeling to WEPP controller"
git commit -m "fix: Handle missing climate data gracefully"
git commit -m "docs: Add examples to Watershed controller"
git commit -m "refactor: Extract common validation logic"
git commit -m "test: Add integration tests for query engine"
```

### Branch Names

```bash
# Format: <type>/<short-description>

feature/add-erosion-analysis
fix/climate-download-timeout
docs/improve-api-reference
refactor/extract-raster-utils
```

## Common Pitfalls (AVOID THESE)

### ❌ Don't: Call `__init__` Directly

```python
# WRONG
controller = MyController(wd)

# CORRECT
controller = MyController.getInstance(wd)
```

### ❌ Don't: Mutate Without Locking

```python
# WRONG
wepp.phosphorus_opts = PhosphorusOpts()

# CORRECT
with wepp.locked():
    wepp.phosphorus_opts = PhosphorusOpts()
    wepp.dump_and_unlock()
```

### ❌ Don't: Forget `dump_and_unlock()`

```python
# WRONG
with wepp.locked():
    wepp.data['key'] = 'value'
# Lock held forever!

# CORRECT
with wepp.locked():
    wepp.data['key'] = 'value'
    wepp.dump_and_unlock()
```

### ❌ Don't: Use String Concatenation for Paths

```python
# WRONG
path = wd + '/' + filename

# CORRECT
from os.path import join as _join
path = _join(wd, filename)
```

### ❌ Don't: Ignore Type Hints

```python
# WRONG
def process(data):
    pass

# CORRECT
def process(data: Dict[str, float]) -> bool:
    pass
```

### ❌ Don't: Skip Docstrings

```python
# WRONG
def complex_function(a, b, c):
    return a + b * c

# CORRECT
def complex_function(a: float, b: float, c: float) -> float:
    """Compute linear combination of parameters.
    
    Args:
        a: Base value
        b: Coefficient
        c: Multiplier
        
    Returns:
        Result of a + b * c
    """
    return a + b * c
```

### ❌ Don't: Mix sync and async code incorrectly

```python
# WRONG - blocking in async context
async def process_run(runid: str):
    time.sleep(10)  # Blocks event loop!

# CORRECT
async def process_run(runid: str):
    await asyncio.sleep(10)

# WRONG - async in sync context without await
def sync_function():
    result = async_function()  # Returns coroutine, doesn't run!

# CORRECT
import asyncio

def sync_function():
    result = asyncio.run(async_function())
```

### ❌ Don't: Hardcode file paths

```python
# WRONG
config_path = '/home/user/wepppy/config.ini'
data_dir = 'C:\\Users\\user\\data'

# CORRECT
from pathlib import Path
import os

config_path = Path(os.environ.get('WEPPPY_CONFIG', 'config.ini'))
data_dir = Path(wd) / 'data'
```

### ❌ Don't: Ignore resource cleanup

```python
# WRONG
def process_file(path: str):
    f = open(path)
    data = f.read()
    return data  # File never closed!

# CORRECT
def process_file(path: str) -> str:
    with open(path) as f:
        data = f.read()
    return data

# Also correct for multiple resources
from contextlib import ExitStack

def process_multiple(paths: List[str]):
    with ExitStack() as stack:
        files = [stack.enter_context(open(p)) for p in paths]
        # All files automatically closed
```

### ❌ Don't: Use mutable default arguments

```python
# WRONG - shared mutable default!
def add_item(item: str, items: List[str] = []):
    items.append(item)
    return items

# CORRECT
def add_item(item: str, items: Optional[List[str]] = None) -> List[str]:
    if items is None:
        items = []
    items.append(item)
    return items
```

## Quality Checklist

Before submitting changes:

- [ ] Code follows existing patterns
- [ ] Type hints added to new functions/methods
- [ ] Docstrings added with examples
- [ ] Tests pass locally (`pytest tests/`)
- [ ] New tests added for new functionality
- [ ] Documentation updated (README, ARCHITECTURE, etc.)
- [ ] `__all__` updated if adding public API
- [ ] NoDb exports follow conventions
- [ ] No secrets in code
- [ ] Redis usage follows DB allocation
- [ ] Locking patterns correct
- [ ] No breaking changes to serialization
- [ ] Commit messages follow conventions

## Troubleshooting

### "Where should I look first?"

```bash
# Find where something is defined
git grep -n "class ClassName"
git grep -n "def function_name"

# Find where something is used
git grep -n "ClassName\|function_name"

# Check recent changes to a file
git log -p --follow -- path/to/file.py

# Find similar implementations
git grep -n "similar_pattern" | head -20
```

### "Why is my NoDb controller not persisting?"

Check these common issues:
1. Did you call `dump_and_unlock()` after mutations?
2. Did you use the `locked()` context manager?
3. Is the working directory writable?
4. Check logs for serialization errors

### "Why are my tests failing?"

1. Run tests with verbose output: `pytest -vv tests/`
2. Check for Redis connection issues
3. Verify temp directory cleanup: `pytest --capture=no`
4. Review test isolation (clear singletons between tests)

## Resources

- **ARCHITECTURE.md** - System design and components
- **AGENTS.md** - Detailed agent coding guide
- **API_REFERENCE.md** - Quick API reference
- **docs/dev-notes/style-guide.md** - Coding conventions
- **docs/dev-notes/redis_dev_notes.md** - Redis patterns
- **wepppy/nodb/base.py** - NoDb implementation reference

---

**Questions?** Check existing implementations:
```bash
# Find similar code
git grep -n "pattern_name"

# View file history
git log -p -- path/to/file.py

# Find all usages
git grep -n "ClassName\|function_name"
```

**Last Updated**: 2025-10-17
