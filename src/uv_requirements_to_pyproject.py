"""
Script to convert requirements.txt based projects to pyproject.toml using UV tool.

Usage:
Copy this script to the same directory as your requirements.txt file and run it.
Example: python uv_requirements_to_pyproject.py

Process:
1. Parses requirements.txt into dependency entries compatible with pyproject.toml
2. Validates the conversion by comparing dependency counts
3. Creates a UV project structure with 'uv init'
4. Updates pyproject.toml with the converted dependencies
5. Runs 'uv sync' to install the dependencies
6. Cleans up temporary files (requirements.txt, .python-version, main.py)

Requirements:
- UV must be installed and accessible in the PATH
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path


def parse_requirements(req_path: Path) -> list[str]:
    """Parse a requirements.txt file and return a list of requirements."""
    requirements: list[str] = []
    with req_path.open("r") as file:
        for line in file:
            # Skip empty lines and comments
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Skip options like --index-url, -f, --find-links, etc.
            if line.startswith("-"):
                continue

            # Handle requirements with comments
            line = line.split("#")[0].strip()

            # Skip if empty after removing comments
            if not line:
                continue

            requirements.append(line)

    return requirements


def format_dependency(req: str) -> str | None:
    """Format a single requirement for pyproject.toml in the format 'package>=1.0.0'."""
    # Remove any extras and environment markers
    req = re.sub(r"\[[^\]]+\]", "", req)
    req = req.split(";")[0].strip()

    # Extract package name (everything before any version specifier)
    name_pattern = re.compile(r"^([a-zA-Z0-9_\-\.]+)")
    name_match = name_pattern.search(req)

    if not name_match:
        return None

    name = name_match.group(1)

    # Common version specifiers: ==, >=, <=, ~=, !=, >, <
    version_pattern = re.compile(r"([=<>!~]+\s*[0-9a-zA-Z\.\-\*]+)")
    version_matches = version_pattern.findall(req)

    if not version_matches:
        # No version specified, use any version
        return f"{name}"

    # Join all version specifiers directly with the package name
    # Example: requests>=2.0.0,<3.0.0 becomes "requests>=2.0.0,<3.0.0"
    versions = ",".join(v.strip() for v in version_matches)
    return f"{name}{versions}"


def generate_dependencies_section(req_path: Path) -> str:
    """Generate a dependencies list for pyproject.toml from requirements.txt."""
    requirements = parse_requirements(req_path)

    # Format each requirement for pyproject.toml
    formatted_deps: list[str] = []
    for req in requirements:
        formatted = format_dependency(req)
        if formatted:
            formatted_deps.append(f'    "{formatted}",')

    # Generate the dependencies section
    if not formatted_deps:
        deps_section = "dependencies = [\n]"
    else:
        deps_section = "dependencies = [\n"
        deps_section += "\n".join(formatted_deps)
        deps_section += "\n]"

    return deps_section


def validate_requirement_conversion(req_path: Path, generated_dependencies: str) -> bool:
    """Test that the conversion worked correctly by comparing item counts."""
    # Get the original requirements count
    requirements = parse_requirements(req_path)
    original_count = len(requirements)

    # Clean up generated dependencies
    output_lines = [line for line in generated_dependencies.split("\n") if line.strip() not in ["dependencies = [", "]"]]
    output_count = len(output_lines)

    # Compare counts
    if original_count == output_count:
        print(f"{original_count} requirements converted to {output_count} dependencies")
        return True
    else:
        print(f"❌ Validation failed: {original_count} requirements != {output_count} dependencies")
        # Print items that might have been skipped or duplicated
        if original_count > output_count:
            print("Some requirements may have been skipped. Check for invalid formats.")
        else:
            print("Output has more items than input. Check for duplicates.")
        return False


def copy_dependencies_to_pyproject(pyproject_path: Path, dependencies: str):
    """Copy the dependencies section into the pyproject.toml file."""
    if not pyproject_path.exists():
        return False

    # Find and replace dependencies
    content = pyproject_path.read_text()
    updated_content = re.sub(
        r"dependencies\s*=\s*\[[\s\S]*?\]",
        dependencies,
        content,
    )
    success = pyproject_path.write_text(updated_content)
    return success


def run_uv_command(cmd: list[str]) -> bool:
    """Execute a UV command and stream its output to the console."""
    if shutil.which("uv") is not None:
        print(" ".join(cmd))
        try:
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            ) as process:
                # Stream stderr output in real-time
                while True:
                    if process.stderr is None:
                        break
                    line = process.stderr.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        print(line.rstrip())
                # Check if process failed
                if process.returncode != 0:
                    print(f"Error: {process.returncode}")
                    return False
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    else:
        print("Warning: 'uv' command not found. You must install uv to use this script.")
        return False


def main() -> None:
    """
    - Locates requirements.txt file
    - Generates dependencies section for pyproject.toml
    - Tests the conversion for completeness
    - Sets up a UV project and copies dependencies to pyproject.toml
    - Runs UV sync to install dependencies
    - Cleans up unneeded files
    """
    # Get the script directory for default path
    script_dir = Path(__file__).parent
    req_path = script_dir / "requirements.txt"

    if not req_path.exists():
        print(f"Error: File {req_path} does not exist.")
        sys.exit(1)

    # Generate dependencies section
    dependencies_section = generate_dependencies_section(req_path)

    # Run test
    success = validate_requirement_conversion(req_path, dependencies_section)
    if not success:
        sys.exit(1)

    # Run uv init to set up the project
    cmd = ["uv", "init"]
    success = run_uv_command(cmd)
    if not success:
        sys.exit(1)

    # Copy dependencies to pyproject.toml
    pyproject_path = script_dir / "pyproject.toml"
    success = copy_dependencies_to_pyproject(pyproject_path, dependencies_section)
    if success:
        print(f"Copied dependencies to {pyproject_path.name}")
    else:
        print(f"Error: Could not write to {pyproject_path}")
        sys.exit(1)

    # Run uv sync
    cmd = ["uv", "sync"]
    success = run_uv_command(cmd)
    if not success:
        sys.exit(1)

    # Remove unneeded files
    files_to_remove = [
        script_dir / "requirements.txt",
        script_dir / ".python-version",
        script_dir / "main.py",
    ]
    for file in files_to_remove:
        file.unlink()
        print(f"Removed {file.name}")


if __name__ == "__main__":
    main()
