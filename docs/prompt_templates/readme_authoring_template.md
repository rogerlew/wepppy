# README Authoring Template and Guidance

> **Purpose**: Provides a standard template for authoring and refining README.md documents across the wepppy repository, serving multiple audiences: GitHub visitors, web indexers, domain experts (hydrologists, land managers), and developers (human and AI agents).

## Template Structure

Every README.md should follow this general structure, adapting sections as appropriate for the module type and audience:

```markdown
# [Module/Service/Package Name]

> **Brief tagline** (1-2 sentences describing the core purpose)

> **See also:** [AGENTS.md](path/to/AGENTS.md) for [relevant section name] (if applicable)

## Overview

[2-4 paragraphs providing context]
- What problem does this solve?
- Where does it fit in the overall system?
- Who are the primary users/consumers?
- Key capabilities at a glance

## [Module-Specific Core Section]

Choose the most appropriate section title based on module type:
- **Architecture** (for system-level components)
- **Components** (for multi-part modules)
- **Workflow** (for pipeline/process modules)
- **API** (for service interfaces)
- **Usage** (for utilities/tools)

[Detailed explanation with subsections as needed]

## Installation / Setup

[If applicable - deployment, configuration, dependencies]

## Quick Start / Examples

[Concrete usage examples that new users can follow]

```python
# or shell commands, or configuration samples
```

## Configuration

[If applicable - environment variables, config files, options]

| Parameter | Default | Description |
|-----------|---------|-------------|
| `PARAM_NAME` | `value` | What it does |

## Key Concepts / Domain Model

[If applicable - explain domain-specific terminology and relationships]

## Developer Notes

[Information specifically for developers extending or maintaining the code]
- Code organization
- Testing strategy
- Common patterns
- Known limitations

## Operational Notes

[If applicable - deployment, monitoring, troubleshooting]
- Health checks
- Logging
- Metrics
- Common issues and solutions

## Further Reading

- Link to related documentation
- External references
- Relevant dev-notes
- Related modules

## Credits / License

[If applicable - attribution, licensing information]
```

## Audience-Specific Guidance

### For GitHub/Web Visitors (Landing Page)
- **Lead with the tagline**: Make the first sentence compelling and self-contained
- **Use the overview**: Provide enough context that someone unfamiliar can understand the value
- **Include examples**: Show, don't just tell - concrete examples help people evaluate fit
- **Link to deeper docs**: Reference AGENTS.md, API docs, and other resources for details

### For Domain Experts (Hydrologists, Land Managers)
- **Domain Model section**: Explain technical concepts in domain terms
- **Examples with context**: Show how the module supports their workflows
- **Units and standards**: Be explicit about measurement units, coordinate systems, etc.
- **Scientific references**: Link to papers, models, or standards implemented

### For Developers (Human and AI)
- **Developer Notes section**: Technical implementation details, patterns, gotchas
- **Code organization**: How files/classes are structured
- **Testing**: How to validate changes
- **Integration points**: How this module interacts with others
- **AGENTS.md cross-reference**: Link to relevant sections for coding conventions

### For AI Coding Agents
- **Structured information**: Use consistent headings and formatting
- **Explicit patterns**: Document conventions, naming schemes, and idioms
- **Examples with context**: Show typical usage patterns
- **Link to AGENTS.md**: Ensure AI agents can find coding standards and workflows

## Module Type Templates

### NoDb Controller Module

```markdown
# [Controller Name] NoDb Controller

> Manages [domain concept] state for WEPPcloud runs via the NoDb singleton pattern.

> **See also:** [AGENTS.md](../../AGENTS.md) for Working with NoDb Controllers section.

## Overview

[Explain what domain concept this controller manages, how it fits in the run lifecycle]

## Key Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `attribute_name` | `type` | What it stores |

## Usage

```python
from wepppy.nodb.core import ControllerName

controller = ControllerName.getInstance(wd)
with controller.locked():
    controller.attribute = value
    controller.dump_and_unlock()
```

## Integration Points

- **Depends on**: [Other controllers or services]
- **Used by**: [Consumers of this controller]
- **RQ tasks**: [Background jobs that interact with this controller]

## Persistence

- **Filename**: `controller_name.nodb`
- **Redis cache**: DB 13, 72-hour TTL
- **Locking**: Required for all mutations

## Developer Notes

[Implementation details, schema versioning, transient fields]
```

### Microservice

```markdown
# [Service Name] Microservice

> **See also:** [AGENTS.md](../../AGENTS.md) for [Go/Python] Microservices section.

## Purpose

[What problem this service solves, why it was built]

## Architecture

[Service design, technology stack, key components]

## Configuration

[Environment variables and their meanings]

## API Endpoints

| Method & Path | Description | Auth |
|---------------|-------------|------|
| `GET /path` | What it does | Required scopes |

## Deployment

[How to run locally, in Docker, in production]

## Monitoring

[Health checks, metrics, logging patterns]

## Developer Notes

[Build instructions, testing, code organization]
```

### Route/Blueprint

```markdown
# [Feature Name] Routes

> **See also:** [AGENTS.md](../../../../AGENTS.md) for Flask web application structure.

## Purpose

[What user-facing feature this blueprint provides]

## Routes

| Path | Method | Description |
|------|--------|-------------|
| `/path` | `GET` | What it does |

## Templates

[Associated template files and their purpose]

## Frontend Integration

[JavaScript controllers, WebSocket connections, etc.]

## Developer Notes

[Blueprint registration, authorization patterns, common helpers]
```

### Utility/Tool Module

```markdown
# [Tool Name]

> [One-line description of what the tool does]

## Usage

```bash
# Command-line usage
tool-name --option value
```

```python
# Python API usage
from wepppy.module import tool_function
result = tool_function(args)
```

## Options

[Detailed parameter descriptions]

## Examples

[Real-world usage scenarios]

## Developer Notes

[Implementation approach, testing, extending]
```

## Best Practices

### Writing Style
- **Be concise**: Start with essential information, expand in later sections
- **Use active voice**: "This module manages..." not "Management is performed by..."
- **Define acronyms**: Spell out acronyms on first use (e.g., "Redis Queue (RQ)")
- **Use examples**: Code snippets are more valuable than paragraphs of description
- **Keep it updated**: READMEs should evolve with the code

### Structural Conventions
- **H1 for title**: Only one H1 heading (the module name)
- **H2 for major sections**: Overview, Usage, etc.
- **H3 for subsections**: Break down complex sections
- **Tables for structured data**: Parameters, endpoints, attributes
- **Code fences with language**: ` ```python ` or ` ```bash `
- **Consistent cross-references**: Use relative paths, check links work

### Content Priorities
1. **What it is**: Clear, concise explanation of purpose
2. **Why it exists**: Problem it solves, context in the system
3. **How to use it**: Practical examples
4. **How it works**: Implementation details (for developers)
5. **How to extend**: Patterns for adding features (for developers)

### Linking Strategy
- **Link to AGENTS.md**: For coding conventions and patterns
- **Link to main readme.md**: For architecture context
- **Link to API_REFERENCE.md**: For API details
- **Link to dev-notes**: For in-depth technical discussions
- **Use relative paths**: So links work in GitHub and local clones

## Maintenance Workflow

When creating or updating a README.md:

1. **Start with the audience**: Who will read this? What do they need to know?
2. **Choose the right template**: Select the module type template that best fits
3. **Fill in required sections**: Overview, usage/API, and developer notes are mandatory
4. **Add optional sections**: Configuration, troubleshooting, etc. as needed
5. **Include examples**: Real code snippets or command-line examples
6. **Cross-reference AGENTS.md**: Link to relevant sections for deeper technical content
7. **Validate links**: Ensure all internal links work
8. **Normalize spelling**: Run `uk2us` on the completed README (preview changes first!)
9. **Review for completeness**: Does it serve all target audiences?

## Quality Checklist

- [ ] Title (H1) clearly identifies the module
- [ ] Tagline/overview answers "what is this?"
- [ ] Target audiences can find relevant information
- [ ] Examples are concrete and runnable
- [ ] Cross-references to AGENTS.md where appropriate
- [ ] Tables use consistent formatting
- [ ] Code blocks specify language for syntax highlighting
- [ ] Links use relative paths and are valid
- [ ] Spelling normalized to American English (uk2us)
- [ ] No confidential information or hardcoded secrets

## Special Considerations

### For Submodules
If the module is a git submodule or external dependency:
- Keep the README focused on integration with wepppy
- Link to the upstream README for comprehensive documentation
- Document any wepppy-specific configuration or usage patterns

### For Legacy Code
If documenting legacy code:
- Be honest about limitations or deprecated patterns
- Provide migration guidance if a replacement exists
- Document quirks that developers need to know
- Don't invest in comprehensive docs for code slated for removal

### For Experimental Features
If documenting experimental or alpha features:
- Clearly label the status at the top
- Explain stability expectations
- Provide contact information for feedback
- Document known limitations prominently

## README.md Audit Results

The following README.md files in the repository have been assessed. Recommendations are provided for improvement priority:

### Comprehensive (No Action Needed)
- `/readme.md` - Main repository README, comprehensive and well-structured
- `/wepppy/nodb/README.md` - Excellent NoDb documentation with all key sections
- `/services/status2/README.md` - Detailed microservice specification
- `/wepppy/nodb/mods/ash_transport/README.md` - Thorough domain module documentation
- `/docker/README.md` - Comprehensive Docker development guide
- `/wepppy/query_engine/README.md` - Complete API specification

### Good (Minor Updates Suggested)
- `/wepppy/weppcloud/README.md` - Good structure, could expand with examples
- `/wepppy/microservices/README.md` - Brief but adequate with proper links
- `/wepppy/weppcloud/routes/command_bar/README.md` - Good technical content
- `/wepppy/weppcloud/controllers_js/README.md` - Likely good (not fully reviewed)

### Minimal (Needs Expansion)
- `/tests/README.md` - Only contains test command, needs overview and guidelines
- `/wepppy/all_your_base/README.md` - Just an image, needs explanation
- `/wepppy/wepp/soils/README.md` - Technical params only, needs context
- `/wepppy/wepp/management/data/UnDisturbed/README.md` - Likely needs content
- `/wctl/README.md` - Needs usage guide
- `/weppcloudR/README.md` - Needs content (not reviewed)
- `/weppcloudR/templates/README.md` - Needs content (not reviewed)

### Route/Blueprint READMEs (Structure Needed)
- `/wepppy/weppcloud/routes/batch_runner/README.md`
- `/wepppy/weppcloud/routes/diff/README.md`
- `/wepppy/weppcloud/routes/nodb_api/README.md`

### Service READMEs (Review Needed)
- `/services/preflight2/README.md` - Similar to status2, likely comprehensive
- `/wepppy/weppcloud/static-src/README.md` - Static asset build process
- `/wepppy/weppcloud/static-src/vendor-sources/purecss/README.md` - External

### Module READMEs (Context Needed)
- `/wepppy/tools/migrations/README.md` - Migration system documentation
- `/wepppy/topo/wbt/README.md` - WhiteboxTools integration
- `/wepppy/wepp/reports/README.md` - Reporting system
- `/wepppy/nodb/mods/omni/README.md` - Optional mod
- `/wepppy/nodb/mods/ash_transport/dev/README.md` - Dev notes for ash transport

## Template Versioning

- **Version**: 1.0
- **Last Updated**: 2025-10-20
- **Maintainer**: AI Coding Agents (per AGENTS.md authorship policy)

## Meta

**This document and all template guidance in this file are maintained by AI Coding Agents per the AGENTS.md authorship policy. Agents may revise this template as standards evolve or new module types emerge.**
