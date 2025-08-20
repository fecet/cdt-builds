# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the conda-forge CDT (Core Dependency Tree) builds repository that generates conda package recipes from RPM repositories. It converts system libraries from CentOS 7, AlmaLinux 8, and AlmaLinux 9 into conda packages for the conda-forge ecosystem.

## Development Environment Setup

```bash
# Install dependencies using pixi (preferred)
pixi install

# Alternative: create conda environment
conda env create -f env.yml
```

## Core Commands

### Generate CDT Recipes
```bash
# Generate only missing CDT recipes (incremental)
python gen_cdt_recipes.py

# Regenerate ALL CDT recipes (takes 10-20 minutes)
python gen_cdt_recipes.py --force

# Use global cache for faster generation (may have race conditions)
python gen_cdt_recipes.py --fast

# Keep URL changes (requires build number bump)
python gen_cdt_recipes.py --keep-url-changes
```

### Generate Single CDT Recipe
```bash
# Generate recipe for specific package/distro/architecture
python rpm.py PACKAGE_NAME --output-dir=cdts --architecture=x86_64 --distro=alma9 --conda-forge-style

# Example: Generate audit-libs for AlmaLinux 9 x86_64
python rpm.py audit-libs --output-dir=cdts --architecture=x86_64 --distro=alma9 --conda-forge-style
```

### Build CDT Recipes
```bash
# Build specific CDT recipes
python build_cdt_recipes.py

# Print all package names that would be generated
python print_all_pkg_names.py
```

### Documentation Management
```bash
# Update README.md from template (auto-generates package table)
python render_readme.py
```

## Architecture Overview

### Data Flow
```
cdt_slugs.yaml → gen_cdt_recipes.py → rpm.py → cdts/package-distro-arch/
                       ↓                ↓              ↓
                   Configuration    RPM Metadata    conda recipes
                                   (from web repos)   (meta.yaml + build.sh)
```

### Core Components

**Configuration Layer:**
- `cdt_slugs.yaml` - Master configuration defining which packages to build and their special handling rules
- `conda_build_config.yaml` - Build number and variant configuration

**Generation Engine:**
- `gen_cdt_recipes.py` - Main orchestrator that reads configuration and spawns parallel rpm.py processes
- `rpm.py` - Core engine that downloads RPM repository metadata and generates conda recipes
- `cdt_config.py` - Path constants and utility functions

**Post-Processing:**
- Fixes licenses, dependencies, and build scripts based on configuration
- Handles custom CDT overlaps and cleanup

**Build & Utility:**
- `build_cdt_recipes.py` - Builds the generated conda recipes
- `render_readme.py` - Updates README.md from template with current package list
- `print_all_pkg_names.py` - Lists all package names that would be generated

### Directory Structure
- `cdts/` - Auto-generated conda recipes (do not edit manually)
- `custom_cdts/` - Manually maintained custom CDT recipes
- `licenses/` - License files referenced by recipes

## Configuration System

### cdt_slugs.yaml Structure
- `allowlists` - Defines which packages are built for each distro (centos7, alma8, alma9)
- `build_defs` - Per-package configuration with keys:
  - `custom: true/false` - Whether recipe is manually maintained
  - `license_file` - License file path(s) to copy
  - `dep_remove` - Dependencies to remove from recipe
  - `dep_replace` - Dependencies to replace (aliased RPMs)
  - `subfolder` - Repository subfolder per distro (BaseOS, AppStream, CRB, PowerTools)
  - `build_append` - Shell code to append to build scripts

### Supported Distros and Repositories
- **centos7**: CentOS 7.9.2009 from vault.centos.org
- **alma8**: AlmaLinux 8.9 from vault.almalinux.org (BaseOS, AppStream, PowerTools)
- **alma9**: AlmaLinux 9.4 from vault.almalinux.org (BaseOS, AppStream, CRB, devel)

## Development Workflow

### Adding New CDT Package
1. Add package name to appropriate allowlist in `cdt_slugs.yaml`
2. Add package configuration in `build_defs` section
3. Run `python gen_cdt_recipes.py`
4. Commit changes

### Modifying CDT Generation Logic
1. Bump `cdt_build_number` in `conda_build_config.yaml`
2. Modify `rpm.py` or `gen_cdt_recipes.py`
3. Run `python gen_cdt_recipes.py --force` to regenerate all recipes
4. Commit all changes

### Important Notes
- README.md is auto-generated from README.md.tmpl - edit the template, not README.md directly
- Package naming follows pattern: `{package}-{distro}-{arch}` for recipes, `{package}-conda-{arch}` for built packages
- The `--force` flag is expensive (10-20 minutes) but necessary after changing generation logic
- All recipes must use `{{ cdt_build_number }}` or `{{ cdt_build_number|int + 1000 }}` for build numbers