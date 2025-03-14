"""
Script to convert requirements.txt to dependencies list for pyproject.toml for uv project
Usage:
Execute the script with:
python3 requirementstxt_to_uv_pyprojecttoml.py [path/to/requirements.txt]
If no path is provided, it will use 'requirements.txt' in the script's directory.
You can add an optional --validate flag to cross check if number of items in the generated dependency list matches the number of items in the requirements.txt.
Eg: python3 requirementstxt_to_uv_pyprojecttoml.py path/to/requirements.txt --validate
   python3 requirementstxt_to_uv_pyprojecttoml.py --validate
---
Output:
The extracted dependency list is printed out to the terminal - copy and paste it to the target pyproject.toml's [project] section.
If you add the --validate flag, a check will be run at the end and report if ✅ Validation successful or ❌ Validation failed (with failure mode)
Credits:
C3.7S-RM
"""

import re
import sys
from pathlib import Path


def parse_requirements(req_path: Path) -> list[str]:
    """Parse a requirements.txt file and return a list of requirements."""
    requirements = []

    with open(req_path, "r") as file:
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
    formatted_deps = []
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


def test_conversion(req_path: Path, generated_dependencies: str) -> bool:
    """Test that the conversion worked correctly by comparing item counts."""
    # Get the original requirements count
    requirements = parse_requirements(req_path)
    original_count = len(requirements)

    # Clean up generated dependencies
    output_lines = [line for line in generated_dependencies.split("\n") if line.strip() not in ["dependencies = [", "]"]]
    output_count = len(output_lines)

    # Compare counts
    if original_count == output_count:
        print(f"✅ Validation successful: {original_count} requirements converted to {output_count} dependencies")
        return True
    else:
        print(f"❌ Validation failed: {original_count} requirements != {output_count} dependencies")
        # Print items that might have been skipped or duplicated
        if original_count > output_count:
            print("Some requirements may have been skipped. Check for invalid formats.")
        else:
            print("Output has more items than input. Check for duplicates.")
        return False


def main() -> None:
    # Get the script directory for default path
    script_dir = Path(__file__).parent
    default_req_path = script_dir / "requirements.txt"

    validate = False
    req_path = default_req_path

    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--validate":
            validate = True
        else:
            req_path = Path(sys.argv[1])
            if len(sys.argv) > 2 and sys.argv[2] == "--validate":
                validate = True

    if not req_path.exists():
        print(f"Error: File {req_path} does not exist.")
        print(f"Usage: {sys.argv[0]} [path/to/requirements.txt] [--validate]")
        sys.exit(1)

    # Generate dependencies section
    dependencies_section: str = generate_dependencies_section(req_path)
    print(dependencies_section)

    # Run test if requested
    if validate:
        success: bool = test_conversion(req_path, dependencies_section)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
