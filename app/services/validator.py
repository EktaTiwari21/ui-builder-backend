import re
from dataclasses import dataclass, field

@dataclass
class ValidationResult:
    """Dataclass representing the validation outcome of a code component."""
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

def validate(code: str) -> ValidationResult:
    """Validate React component code for style, security, structure, and package imports.
    
    Args:
        code: React JSX component code string.
        
    Returns:
        ValidationResult: contains validity flag, list of errors, and list of warnings.
    """
    errors = []
    warnings = []
    
    if not code or not code.strip():
        return ValidationResult(is_valid=False, errors=["Empty or whitespace-only code block."], warnings=[])

    # Strip code comments to prevent scanning them for imports/dangerous keywords
    # 1. Multi-line comments: /* ... */
    # 2. Single-line comments: // ...
    code_no_comments = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    code_no_comments = re.sub(r"//.*", "", code_no_comments)

    # Check 1: Named Export Check
    # Must contain "export function" or "export const" or "export class"
    export_pattern = re.compile(r"\bexport\s+(?:function|const|class|async\s+function)\b")
    if not export_pattern.search(code_no_comments):
        errors.append("Missing named export: Component must have at least one named export (e.g. 'export function MyComponent').")

    # Check 2: Unsafe/Dangerous patterns
    dangerous_keywords = {
        "eval(": "eval() function execution",
        "dangerouslySetInnerHTML": "dangerouslySetInnerHTML React property",
        "document.write": "document.write() direct document insertion"
    }
    for kw, description in dangerous_keywords.items():
        if kw in code_no_comments:
            errors.append(f"Dangerous pattern detected: Use of {description} is strictly prohibited.")

    # Check 3: Tailwind CSS Class presence
    if "className=" not in code_no_comments:
        errors.append("Tailwind CSS check failed: Code must contain at least one Tailwind class indicator (className=).")

    # Check 4: Import validation (Only react and lucide-react allowed)
    import_pattern = re.compile(r"""import\s+.*?\s+from\s+['"]([^'"]+)['"]""")
    imports = import_pattern.findall(code_no_comments)
    allowed_packages = {"react", "lucide-react"}
    for imp in imports:
        if imp not in allowed_packages:
            errors.append(f"Import from unauthorized package: '{imp}'. Only 'react' and 'lucide-react' imports are allowed.")

    # Check 5: Basic JSX Tag Balance Check
    tag_errors = _check_tags_balanced(code_no_comments)
    errors.extend(tag_errors)

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)

def _check_tags_balanced(code: str) -> list[str]:
    """Helper method to check if JSX tags are balanced using a simple tag stack."""
    errors = []
    # Match tag names, supporting components (e.g. Dialog.Title) or standard HTML tags.
    # Group 1 matches standard tag or component tag (e.g. /?div or /?Dialog.Title)
    # Group 2 matches the optional closing slash for self-closing tags (e.g. <img />)
    tag_pattern = re.compile(r"<(/?[a-zA-Z][a-zA-Z0-9\._-]*)(?:\s+[^>]*?)?(/?)>", re.DOTALL)
    matches = tag_pattern.findall(code)
    
    stack = []
    for tag_name, self_closing in matches:
        # If it's a self-closing tag (ends with /), skip pushing to stack
        if self_closing == "/":
            continue
            
        if tag_name.startswith("/"):
            # Closing tag (e.g. </div>)
            name = tag_name[1:]
            if not stack:
                errors.append(f"Unbalanced closing tag: </{name}> with no matching opening tag.")
            else:
                top = stack.pop()
                if top != name:
                    errors.append(f"Mismatched tags: open <{top}> closed </{name}>.")
        else:
            # Opening tag
            stack.append(tag_name)
            
    while stack:
        top = stack.pop()
        errors.append(f"Unbalanced opening tag: <{top}> with no matching closing tag.")
        
    return errors
