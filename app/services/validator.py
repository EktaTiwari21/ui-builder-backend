import re
from dataclasses import dataclass, field

# HTML void elements — never need a closing tag
HTML_VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr"
}

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

    # Check 1: Export Check
    # Must contain "export function", "export const", "export class", or "export default"
    export_pattern = re.compile(r"\bexport\s+(?:default\s+)?(?:function|const|class|async\s+function)\b|\bexport\s+default\s+[a-zA-Z0-9_]+\b")
    if not export_pattern.search(code_no_comments):
        errors.append("Missing named export: Component must have at least one named export or default export (e.g. 'export function MyComponent' or 'export default MyComponent').")

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
    if "className=" not in code:
        errors.append("Tailwind CSS check failed: Code must contain at least one Tailwind class indicator (className=).")

    # Check 4: Import validation — only safe packages allowed (warnings, not errors)
    import_pattern = re.compile(r"""import\s+.*?\s+from\s+['"]([^'"]+)['"]""")
    imports = import_pattern.findall(code_no_comments)
    allowed_packages = {
        "react",
        "lucide-react",
        "react-dom",
        "react/jsx-runtime",
        "react/jsx-dev-runtime",
    }
    for imp in imports:
        # Allow relative imports (starting with . or /)
        if imp.startswith(".") or imp.startswith("/"):
            continue
        if imp not in allowed_packages:
            warnings.append(f"Import from potentially unauthorized package: '{imp}'. Preferred: 'react' and 'lucide-react'.")

    # Check 5: Basic JSX Tag Balance Check (lenient — warns only, does not fail)
    tag_errors = _check_tags_balanced(code_no_comments)
    if tag_errors:
        # JSX balance issues are warnings, not hard errors
        # Complex JSX with fragments, ternaries and maps frequently triggers
        # false positives in regex-based parsers
        warnings.extend(tag_errors)

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)

def _check_tags_balanced(code: str) -> list[str]:
    """Helper method to check if JSX tags are balanced using a simple tag stack.
    
    Note: This is a best-effort check. Complex JSX with fragments, ternary renders,
    and mapped components can produce false positives. Results are treated as warnings.
    """
    issues = []
    # Match tag names, supporting components (e.g. Dialog.Title) or standard HTML tags.
    # Group 1 matches standard tag or component tag (e.g. /?div or /?Dialog.Title)
    # Group 2 matches the optional closing slash for self-closing tags (e.g. <img />)
    tag_pattern = re.compile(r"<(/?[a-zA-Z][a-zA-Z0-9\._-]*)(?:\s+[^>]*)?(/?)\s*>", re.DOTALL)
    matches = tag_pattern.findall(code)
    
    stack = []
    for tag_name, self_closing in matches:
        # Skip JSX fragments (empty tag name effectively, matched as <>)
        if not tag_name or tag_name in ("", "/"):
            continue

        # If it's a self-closing tag (ends with /), skip pushing to stack
        if self_closing == "/":
            continue

        # Remove leading slash for closing tag check
        is_closing = tag_name.startswith("/")
        clean_name = tag_name[1:] if is_closing else tag_name

        # Skip void HTML elements — they never have closing tags
        if clean_name.lower() in HTML_VOID_ELEMENTS and not is_closing:
            continue

        if is_closing:
            # Closing tag (e.g. </div>)
            if not stack:
                issues.append(f"Unbalanced closing tag: </{clean_name}> with no matching opening tag.")
            else:
                top = stack.pop()
                if top.lower() != clean_name.lower():
                    issues.append(f"Mismatched tags: open <{top}> closed </{clean_name}>.")
        else:
            # Opening tag
            stack.append(tag_name)
            
    while stack:
        top = stack.pop()
        issues.append(f"Unbalanced opening tag: <{top}> with no matching closing tag.")
        
    return issues
