# Agent Accessibility Survey - Living Document

> **Last Updated**: 2025-10-23  
> **Initial Survey**: 2025-10-18  
> **Repository**: rogerlew/wepppy  
> **Status**: Living Document - Update quarterly or after major milestones

## Purpose

This living document tracks the WEPPpy repository's accessibility for AI coding agents (GitHub Copilot, Claude, Gemini, etc.). It serves as both a historical record of improvements and an ongoing assessment tool to guide future work.

**Update Triggers**:
- Quarterly reviews (Jan, Apr, Jul, Oct)
- Completion of major documentation initiatives
- Significant architectural changes
- Addition of new modules or subsystems

**How to Update This Document**:

When you make significant improvements to agent accessibility, update the relevant sections:

1. **Metrics Table** - Update quantitative measurements
2. **Phase Status** - Change status from 🔄 to ✅ when complete
3. **Recent Work Packages** - Add new entries for significant work
4. **Change Log** - Record the update with date and summary
5. **Priorities** - Adjust based on completed work and new needs

**Agent Authority**: AI agents maintain this document and have full authority to update it. Keep it accurate, concise, and actionable.

## Executive Summary

This document began as a comprehensive accessibility survey in October 2025 and now serves as a living tracker of improvements made to enhance agent-assisted development across the codebase.

## Survey Methodology

The survey examined:
- Documentation structure and completeness
- Code organization and discoverability
- API documentation and examples
- Type hints and inline documentation
- Cross-referencing and navigation aids
- Testing patterns and examples
- Data structure schemas

## Key Findings

### Strengths Identified

1. **Excellent High-Level Documentation**
   - Comprehensive AGENTS.md already existed
   - Well-written readme.md with clear architecture overview
   - Good dev-notes covering specific topics

2. **Strong Code Organization**
   - Clear module hierarchy (nodb/core, nodb/mods)
   - Explicit `__all__` exports in most modules
   - Consistent naming conventions
   - Well-structured directory layout

3. **Good Patterns**
   - Singleton pattern consistently applied
   - Context managers for locking
   - Event-driven architecture well-documented
   - Redis usage patterns clearly defined

### Deficiencies Identified

1. **Documentation Gaps**
   - ❌ No centralized architecture documentation with diagrams
   - ❌ No API reference document for quick lookup
   - ❌ Missing module-level docstrings in most files
   - ❌ Inconsistent function/method docstrings
   - ❌ No agent-specific contribution guide
   - ❌ No structured JSON schemas for data formats

2. **Type Hints**
   - ❌ Limited type hints (only ClassVar, Optional in base.py)
   - ❌ Most functions lack type annotations
   - ❌ No .pyi stub files for external APIs

3. **Examples and Cross-References**
   - ❌ Limited inline code examples
   - ❌ Few cross-references between related components
   - ❌ No quick-start guides for common tasks

4. **Discoverability**
   - ❌ Test structure not immediately obvious
   - ❌ No API catalog or index
   - ❌ Component relationships not diagramed

## Implemented Improvements

### Phase 1: Documentation Infrastructure (Completed)

#### 1. ARCHITECTURE.md
**Created**: Comprehensive architectural documentation

**Contents**:
- System overview diagram
- Component interaction patterns
- Data flow diagrams
- Redis database allocation guide
- Technology stack enumeration
- Directory structure map
- Design patterns documentation
- Integration examples

**Impact**: Agents can quickly understand system design without reading code.

#### 2. API_REFERENCE.md
**Created**: Quick reference for common APIs

**Contents**:
- NoDb Controllers API with examples
- Flask Routes API
- Background Jobs API (RQ)
- Query Engine API
- Common code patterns
- Error handling examples

**Impact**: Agents can look up API usage without searching code.

#### 3. CONTRIBUTING_AGENTS.md
**Created**: Agent-specific contribution guide

**Contents**:
- Code organization patterns
- Module structure templates
- Type hints guidelines
- Docstring format (Google-style)
- NoDb controller patterns
- Testing patterns
- Common pitfalls to avoid
- Quality checklist

**Impact**: Agents understand coding conventions and best practices.

#### 4. JSON Schemas
**Created**: docs/schemas/wepppy-data-structures.json

**Contents**:
- NoDb controller serialization schemas
- Query Engine payload/response schemas
- Redis data structure schemas
- WebSocket message schemas
- RQ job metadata schemas

**Impact**: Machine-readable validation and autocomplete support.

#### 5. Updated readme.md
**Modified**: Added documentation index

**Impact**: Single entry point for all documentation resources.

### Phase 2: Module Documentation (Completed)

#### Core NoDb Controllers Documented

Added comprehensive module-level docstrings to:

1. **wepppy/nodb/base.py**
   - NoDb philosophy explanation
   - Locking mechanism details
   - Redis integration guide
   - Serialization overview
   - Usage examples

2. **wepppy/nodb/core/climate.py**
   - Climate data sources enumeration
   - Processing pipeline description
   - Usage examples
   - Cross-references

3. **wepppy/nodb/core/watershed.py**
   - Watershed abstraction overview
   - Delineation backends comparison
   - Data products description
   - Integration notes

4. **wepppy/nodb/core/wepp.py**
   - WEPP model components
   - Input/output files documentation
   - Execution pipeline
   - Examples

5. **wepppy/nodb/core/landuse.py**
   - Land cover sources
   - Management database integration
   - Processing workflow

6. **wepppy/nodb/core/soils.py**
   - Soil data sources
   - Pedotransfer functions
   - Database integration

**Format Used**: Google-style docstrings with:
- Purpose statement
- Key components list
- Data source descriptions
- Usage examples
- See Also references
- Notes and warnings

**Impact**: Immediate context available when viewing module code.

### Phase 3: Type Hints and Stubs (**COMPLETED** - Oct 2025)

**Status**: ✅ **Major progress achieved**

#### Type Hints Implementation
All NoDb core controllers now have **comprehensive type hints**:
- ✅ `climate.py` - Complete (118 annotated methods)
- ✅ `soils.py` - Complete 
- ✅ `landuse.py` - Complete
- ✅ `watershed.py` - Complete
- ✅ `wepp.py` - Complete (2706 lines)
- ✅ `topaz.py` - Complete
- ✅ `ron.py` - Complete

**Type Stub Infrastructure**:
- ✅ 208+ `.pyi` stub files created under `stubs/wepppy/`
- ✅ `mypy.ini` configured with proper paths
- ✅ Validation tooling added:
  - `wctl run-stubtest` - Validates stubs against runtime
  - `wctl check-test-stubs` - Ensures test stubs match public APIs
  - `tools/sync_stubs.py` - Keeps stubs synchronized
  - `tools/check_stubs.py` - Automated stub validation

**NoDb Mods Progress**:
- ✅ `disturbed/disturbed.py` - Complete
- ✅ `path_ce/` modules - Complete (controller, data_loader, solver)
- ✅ `ash_transport/ash.py` - Complete with `.pyi` stub
- ✅ `baer/baer.py` - Complete with `.pyi` stub
- ✅ `rangeland_cover/rangeland_cover.py` - Complete with `.pyi` stub
- ✅ `rap/rap.py` - Complete with `.pyi` stub
- ⚠️ 62 remaining mods need attention (see TYPE_HINTS_SUMMARY.md)

See `TYPE_HINTS_SUMMARY.md` for detailed coverage status.

### Phase 4: Testing Infrastructure (**COMPLETED** - Oct 2025)

**Status**: ✅ **Comprehensive testing documentation and tooling**

#### Test Documentation
- ✅ `tests/README.md` - Comprehensive guide for human developers
- ✅ `tests/AGENTS.md` - Agent-specific testing patterns and best practices
- ✅ Test marker system documented and enforced
- ✅ Test isolation patterns established

#### Testing Tooling
- ✅ `wctl run-pytest` - Run tests in Docker container
- ✅ `wctl check-test-isolation` - Detect order-dependent test failures
- ✅ Marker guidelines for unit/integration/slow/benchmark tests
- ✅ Test stub management patterns documented

### Phase 5: README Documentation (**IN PROGRESS** - Oct 2025)

**Status**: 🔄 **Ongoing improvements**

#### README Template Created
- ✅ Comprehensive template: `docs/prompt_templates/readme_authoring_template.md`
- ✅ Module-specific templates (NoDb controllers, microservices, routes, utilities)
- ✅ Quality standards and maintenance workflow defined
- ✅ Audit of existing READMEs with improvement recommendations

#### README Coverage
- ✅ 64+ README files exist across the repository
- ✅ Key modules documented:
  - `wepppy/nodb/README.md`
  - `wepppy/weppcloud/README.md`
  - `wepppy/query_engine/README.md`
  - `services/status2/README.md`
  - `services/preflight2/README.md`
  - `wctl/README.md`
  - `docker/README.md`
- ⚠️ Many module-level READMEs need expansion (see docs/README_AUDIT.md)

**Next Priorities**:
1. Expand README.md files for high-traffic modules (landuse, soils, watershed)
2. Add README.md to utility packages (all_your_base, wepp/soils/utils)
3. Document microservices comprehensively

### Phase 6: Cross-References and Examples (Medium Priority)

**Status**: 🔄 **Partial implementation**

#### Examples Added
- ✅ Module docstrings now include usage examples
- ✅ API_REFERENCE.md provides concrete patterns
- ✅ CONTRIBUTING_AGENTS.md shows best practices
- ⚠️ More inline examples needed in complex modules

#### Cross-References
- ✅ AGENTS.md extensively cross-references documentation
- ✅ Module docstrings include "See Also" sections
- ⚠️ Inter-module references could be strengthened
- ⚠️ Workflow documentation needs more cross-linking

**Recommended Next Steps**:
1. Add more cross-references in NoDb mod documentation
2. Link related Flask routes and RQ tasks
3. Create workflow diagrams showing component interactions
4. Add "Related Components" sections to key modules

## Impact Assessment

### Quantitative Metrics (Updated 2025-10-23)

| Metric | Oct 2025 Initial | Oct 2025 Current | Improvement |
|--------|------------------|------------------|-------------|
| Documentation files | 2 | 8+ | +300% |
| Module docstrings (core) | 0/7 | 7/7 | **100%** ✅ |
| Type hints (core NoDb) | ~5% | **100%** | **+1900%** ✅ |
| `.pyi` stub files | 0 | 208+ | New ✅ |
| Lines of documentation | ~1000 | ~8000+ | +700% |
| API examples | ~10 | ~80+ | +700% |
| Schemas available | 0 | 1 | New |
| README files | ~50 | 64+ | +28% |
| Testing tooling commands | 0 | 3 | New ✅ |
| NoDb mods documented | 0/68 | 6/68 | +9% 🔄 |

### Key Milestones Achieved

✅ **Phase 1: Documentation Infrastructure** (Oct 2025)
- ARCHITECTURE.md, API_REFERENCE.md, CONTRIBUTING_AGENTS.md created
- JSON schemas published
- readme.md updated with navigation

✅ **Phase 2: Module Documentation** (Oct 2025)
- All 7 core NoDb controllers documented
- Google-style docstrings standardized
- Usage examples added

✅ **Phase 3: Type Hints & Stubs** (Oct 2025)
- All core NoDb controllers fully typed
- 208+ stub files created
- Validation tooling implemented (wctl commands)
- mypy.ini configured

✅ **Phase 4: Testing Infrastructure** (Oct 2025)
- Comprehensive test documentation (README.md, AGENTS.md)
- Test isolation checking tooling
- Stub validation automation
- Marker system documented

🔄 **Phase 5: README Coverage** (In Progress)
- Template created with quality standards
- 64+ README files exist
- High-value modules need expansion

🔄 **Phase 6: Cross-References** (Partial)
- Module docstrings include "See Also"
- AGENTS.md extensively cross-links
- More workflow documentation needed

### Qualitative Benefits

**For AI Agents**:
1. ✅ **Faster Context Acquisition** - Architectural overview reduces exploration time
2. ✅ **Better Pattern Recognition** - Examples show established patterns
3. ✅ **Reduced Errors** - Common pitfalls documented
4. ✅ **Self-Service** - Comprehensive docs reduce need for human input
5. ✅ **Type Safety** - JSON schemas enable validation

**For Human Developers**:
1. ✅ **Easier Onboarding** - New developers understand system faster
2. ✅ **Better Collaboration** - Shared vocabulary and patterns
3. ✅ **Reduced Maintenance** - Clear documentation reduces questions
4. ✅ **Improved Code Quality** - Guidelines promote consistency

## Recommendations for Future Work

### High Priority (Next Quarter)

#### 1. Complete NoDb Mods Documentation (6/68 done)
**Status**: 🔄 In Progress  
**Target**: 20/68 by end of Q4 2025

Focus on high-traffic mods:
- ⚠️ `omni/omni.py` - Core analytics module
- ⚠️ `ag_fields/ag_fields.py` - Agricultural fields support
- ⚠️ `rhem/rhem.py` - RHEM integration
- ⚠️ `debris_flow/debris_flow.py` - User-facing mod
- ⚠️ `treatments/treatments.py` - Treatment scenarios
- ⚠️ `treecanopy/treecanopy.py` - Tree canopy analysis

**Actions**:
1. Add module docstrings following template
2. Add comprehensive type hints
3. Create `.pyi` stubs
4. Validate with `wctl run-stubtest`

#### 2. Expand Module README Files
**Status**: 🔄 Partial  
**Target**: 30 expanded READMEs by end of Q4 2025

Priority modules:
- `wepppy/nodb/mods/` - Individual mod READMEs
- `wepppy/climates/` - Climate data source documentation
- `wepppy/all_your_base/` - Utility functions
- `wepppy/wepp/soils/utils/` - Soil processing utilities

**Actions**:
1. Use `docs/prompt_templates/readme_authoring_template.md`
2. Include concrete examples and workflow diagrams
3. Cross-reference with AGENTS.md

#### 3. CI/CD Integration
**Status**: ⚠️ Not Started  
**Target**: Q1 2026

**Actions**:
1. Add GitHub Actions workflow for type checking
2. Run `mypy` on core modules in CI
3. Add `stubtest` validation
4. Add docstring coverage checking
5. Add test isolation checks
6. Fail PR if coverage drops

### Medium Priority (Q1 2026)

#### 1. Enhanced Workflow Documentation
Create comprehensive workflow guides:
- End-to-end scenario walkthroughs
- Common task recipes
- Troubleshooting guides
- Architecture decision records (ADRs)

#### 2. Interactive Documentation
**Status**: ⚠️ Not Started  
**Estimated Effort**: 2-3 weeks

**Options**:
- Sphinx documentation site with autodoc
- MkDocs with API reference generation
- Docusaurus with interactive examples

**Benefits**:
- Searchable API documentation
- Auto-generated from docstrings
- Version-aware documentation

#### 3. Cross-Reference Enhancement
Systematically add cross-references:
- Between NoDb controllers and consumers
- Between Flask routes and RQ tasks
- Between data producers and consumers
- Between related microservices

### Long-Term Improvements (2026+)

#### 1. Tutorial Series
Create step-by-step tutorials:
- Getting started with wepppy
- Creating a custom NoDb mod
- Adding a new climate data source
- Implementing a background job
- Adding a Flask route

#### 2. Video Documentation (Optional)
Consider video walkthroughs:
- Architecture overview (15 min)
- Code tour for new developers (30 min)
- Common workflows (5-10 min each)

#### 3. Agent Performance Metrics
Track quantitative agent effectiveness:
- Time to first contribution
- PR quality scores
- Code pattern consistency
- Error rates in generated code
- Documentation coverage trends

### Maintenance Strategy

#### Quarterly Review Process
**Schedule**: January, April, July, October

**Checklist**:
- [ ] Update this document with latest metrics
- [ ] Review TYPE_HINTS_SUMMARY.md coverage
- [ ] Audit README_AUDIT.md recommendations
- [ ] Check for new modules needing documentation
- [ ] Review agent-generated code quality
- [ ] Update priorities based on usage patterns

#### Continuous Documentation Standards
**For All New Code**:
- [ ] Module docstring required
- [ ] Type hints on all public functions
- [ ] `.pyi` stub if external-facing
- [ ] README.md for new packages
- [ ] Tests include docstrings
- [ ] Examples in docstrings where helpful

#### Tooling Maintenance
**Monthly**:
- Run `wctl check-test-stubs` to catch stub drift
- Run `wctl check-test-isolation` for test quality
- Update `tools/sync_stubs.py` as needed
- Review mypy errors and fix or suppress appropriately

**As Needed**:
- Update `uk2us` rules for new terminology
- Enhance `wctl` with new validation commands
- Improve stub generation automation

## Conclusion

This survey and improvement effort has significantly enhanced the WEPPpy repository's accessibility for AI coding agents. The addition of:
- Comprehensive architectural documentation
- API reference guides
- Agent-specific contribution guidelines
- JSON schemas
- Module-level docstrings

...provides AI agents with the context and structure needed for effective code generation, analysis, and modification.

The improvements focus on:
- **Structured information** - Clear hierarchies and relationships
- **Examples** - Concrete usage patterns
- **Context** - Purpose and integration points
- **Validation** - Machine-readable schemas
- **Best practices** - Explicit guidelines

While additional improvements (type hints, function docstrings, cross-references) would further enhance accessibility, the current changes provide a solid foundation for agent-assisted development.

## Success Metrics and Validation

### Quantitative Success Criteria

| Metric | Initial (Oct 18) | Current (Oct 23) | Target (Q4 2025) | Status |
|--------|------------------|------------------|------------------|--------|
| Core module type coverage | ~5% | **100%** | 100% | ✅ |
| NoDb mods documented | 0% | 9% | 30% | 🔄 |
| `.pyi` stubs | 0 | 208+ | 300+ | ✅ |
| Test documentation | None | Comprehensive | - | ✅ |
| README coverage (modules) | ~50 | 64+ | 80+ | 🔄 |
| CI/CD integration | None | Manual | Automated | ⚠️ |
| Cross-references per module | ~1 | ~5 | 10+ | 🔄 |

### Qualitative Success Indicators

#### Agent Performance (Self-Assessment)
✅ **Improved**:
1. Can generate NoDb controller code that follows established patterns
2. Can answer architecture questions without extensive code exploration
3. Make fewer errors related to NoDb locking and Redis usage
4. Understand data flow between components quickly
5. Generate type-safe code with proper annotations

🔄 **In Progress**:
1. Understanding complex mod interactions (needs more docs)
2. Navigating between related Flask routes and RQ tasks
3. Finding relevant utility functions in all_your_base
4. Understanding WEPP model file formats

⚠️ **Needs Work**:
1. Discovering appropriate testing patterns for mods
2. Understanding geospatial processing workflows
3. Navigating soil and climate data pipelines
4. Understanding microservice contracts

#### Human Developer Feedback
**To be gathered**: Conduct quarterly surveys with:
- Time-to-first-contribution metrics
- Documentation usefulness ratings
- Code review quality assessment
- Questions/confusion patterns

### Validation Methods

#### Automated Validation (Current)
✅ Available now:
```bash
# Type checking
wctl run-stubtest wepppy.nodb.core

# Test quality
wctl check-test-isolation
wctl check-test-stubs

# Full test suite
wctl run-pytest tests/

# Stub synchronization
python tools/sync_stubs.py
```

#### Manual Validation (Quarterly)
Checklist for quarterly reviews:
- [ ] Review agent-generated PRs for pattern adherence
- [ ] Check docstring completeness in new modules
- [ ] Validate README.md files for accuracy
- [ ] Test workflow documentation by following steps
- [ ] Review cross-references for accuracy
- [ ] Check for broken links in documentation

### Measurement Plan

#### Weekly Metrics (Automated)
- Lines of code with type hints (mypy coverage)
- Number of `.pyi` stub files
- Test isolation violations (wctl check-test-isolation)
- Test coverage percentage

#### Monthly Metrics (Semi-Automated)
- New modules without documentation
- README files needing updates
- Broken cross-references
- Docstring coverage by module

#### Quarterly Metrics (Manual)
- Developer survey results
- Agent performance assessment
- Documentation quality review
- Cross-reference audit
- Update this document with findings

## Recent Work Packages (Oct 2025)

This section tracks significant work packages that improved agent accessibility:

### StatusStream Cleanup (Oct 23, 2025)
**Package**: `docs/work-packages/20251023_statusstream_cleanup/`

**Impact on Agent Accessibility**:
- Removed legacy `ws_client.js` patterns
- Consolidated WebSocket handling into `StatusStream` helper
- Updated controller tests and stubs
- Clarified front-end architecture patterns

**Documentation Updates**:
- Updated front-end testing patterns in `tests/AGENTS.md`
- Refined controller bundling documentation
- Improved test stub management guidance

### Type Hints Comprehensive Rollout (Oct 2025)
**Scope**: All core NoDb controllers + 6 mods

**Impact on Agent Accessibility**:
- Eliminated ambiguity in function signatures
- Enabled IDE autocomplete for agents
- Provided machine-readable API contracts
- Improved code generation accuracy

**Artifacts**:
- `TYPE_HINTS_SUMMARY.md` - Coverage tracking
- 208+ `.pyi` stub files
- `mypy.ini` configuration
- Validation tooling (wctl commands)

---

## Appendices

### A. Documentation Index

**Core Documentation**:
- `readme.md` - Repository overview and architecture
- `AGENTS.md` - Comprehensive agent guide (3800+ lines)
- `ARCHITECTURE.md` - System architecture and design patterns
- `API_REFERENCE.md` - Quick API reference
- `CONTRIBUTING_AGENTS.md` - Agent contribution guidelines
- `TYPE_HINTS_SUMMARY.md` - Type hint coverage tracking

**Testing Documentation**:
- `tests/README.md` - Human testing guide
- `tests/AGENTS.md` - Agent testing patterns
- `docs/dev-notes/test-tooling-spec.md` - Tooling specifications

**Templates**:
- `docs/prompt_templates/readme_authoring_template.md` - README guide
- `docs/prompt_templates/module_documentation_workflow.prompt.md` - Module docs

**Audit Documents**:
- `docs/README_AUDIT.md` - README quality assessment
- `docs/README_TEMPLATE_SUMMARY.md` - Template overview

### B. Tooling Reference

**wctl Commands for Documentation Quality**:
```bash
# Type checking and stubs
wctl run-stubtest wepppy.nodb.core      # Validate stubs
wctl check-test-stubs                    # Check test stubs

# Testing quality
wctl run-pytest tests/                   # Run test suite
wctl check-test-isolation                # Check test isolation

# Development
wctl exec weppcloud bash                 # Shell into container
wctl run-npm lint                        # Front-end linting
wctl run-npm test                        # Front-end tests

# Building
wctl build-static-assets                 # Rebuild JS bundles
```

**Python Tools**:
```bash
# Inside container (wctl exec weppcloud bash)
python tools/sync_stubs.py               # Sync stub files
python tools/check_stubs.py              # Validate stubs
python tools/check_test_isolation.py     # Test isolation

# Text normalization
uk2us -i path/to/file.py                 # American English
```

### C. Key Patterns for Agents

**NoDb Controller Pattern**:
```python
from typing import Optional, Dict, Any
from wepppy.nodb.base import NoDbBase

class MyController(NoDbBase):
    """Controller description.
    
    Key responsibilities and data flow.
    
    Example:
        >>> controller = MyController.getInstance(wd)
        >>> with controller.locked():
        ...     controller.process()
        ...     controller.dump_and_unlock()
    """
    
    def __init__(
        self, 
        wd: str, 
        cfg_fn: str,
        run_group: Optional[str] = None
    ) -> None:
        super().__init__(wd, cfg_fn, run_group=run_group)
        self._data: Dict[str, Any] = {}
    
    @property
    def data(self) -> Dict[str, Any]:
        """Access data dictionary."""
        return self._data
    
    def process(self) -> None:
        """Process data with proper locking."""
        with self.locked():
            # Mutate state
            self._data['key'] = 'value'
            self.dump_and_unlock()
```

**Module `__all__` Export Pattern**:
```python
"""Module docstring."""

class PublicClass:
    """Public class."""
    pass

def public_function() -> None:
    """Public function."""
    pass

def _private_helper() -> None:
    """Private helper."""
    pass

__all__ = [
    'PublicClass',
    'public_function',
]
```

**Test Fixture Pattern**:
```python
import pytest
from typing import Iterator

@pytest.fixture
def working_dir(tmp_path) -> Iterator[str]:
    """Provide isolated working directory."""
    wd = str(tmp_path / "test_run")
    os.makedirs(wd)
    yield wd
    # Cleanup if needed

def test_controller_round_trip(working_dir: str) -> None:
    """Test NoDb serialization."""
    controller = MyController.getInstance(working_dir)
    with controller.locked():
        controller.state = "value"
        controller.dump_and_unlock()
    
    reloaded = MyController.getInstance(working_dir)
    assert reloaded is controller
    assert reloaded.state == "value"
```

### D. Common Pitfalls (Updated)

❌ **Don't**:
- Call NoDb `__init__` directly (use `getInstance()`)
- Mutate NoDb state without `with self.locked():`
- Forget to call `dump_and_unlock()` after mutations
- Use wrong Redis DB number
- Create incomplete test stubs that break other tests
- Skip type hints on new public functions
- Forget to update module `__all__` when adding exports

✅ **Do**:
- Use singleton pattern via `getInstance(wd)`
- Always lock before mutations
- Use appropriate Redis DB (see AGENTS.md)
- Match stub APIs to real module exports
- Add type hints following module patterns
- Keep `__all__` synchronized
- Run validation tools before committing
- Update this document after major changes

---

## Change Log

### 2025-10-23
- **Status**: Converted to living document
- **Added**: Recent work packages section
- **Updated**: All metrics to reflect Oct 23 status
- **Updated**: Phases 3-6 to show actual completion status
- **Added**: Quarterly review process
- **Added**: Validation methods and tooling reference
- **Added**: Common patterns appendix
- **Added**: Change log section

### 2025-10-18
- **Initial**: Survey completed and document created
- **Status**: Phases 1-2 completed (documentation infrastructure and core modules)

---

**Document Maintained By**: GitHub Copilot and AI Coding Agents  
**Next Review**: 2026-01-23 (Quarterly)  
**Contact**: See AGENTS.md for contribution process
