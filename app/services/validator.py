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

    # Check 5: Basic JSX Tag Balance Check (strict error)
    tag_errors = _check_tags_balanced(code_no_comments)
    if tag_errors:
        errors.extend(tag_errors)

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)

HTML_TAGS = {
    "div", "span", "p", "a", "button", "img", "input", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "section", "nav", "footer", "header", "main", "aside", "form", "label",
    "select", "option", "textarea", "br", "hr", "svg", "path", "circle", "rect", "g",
    "polygon", "polyline", "line", "text", "tspan", "iframe", "canvas", "video", "audio",
    "table", "thead", "tbody", "tr", "th", "td", "details", "summary", "fieldset", "legend"
}

def is_valid_jsx_tag(tag_name: str) -> bool:
    """Check if a matched tag name is a valid JSX HTML tag or a React Component."""
    clean_name = tag_name[1:] if tag_name.startswith("/") else tag_name
    if not clean_name:
        return False
    # 1. React custom component (starts with uppercase)
    if clean_name[0].isupper():
        return True
    # 2. Standard HTML tag
    if clean_name.lower() in HTML_TAGS:
        return True
    return False

def extract_jsx_tags(code: str) -> list[tuple[str, bool, bool]]:
    """Tokenize JSX tags character by character, handling quotes and braces to bypass comparisons."""
    i = 0
    n = len(code)
    tags = []
    
    in_double_quote = False
    in_single_quote = False
    in_backtick = False
    
    while i < n:
        c = code[i]
        
        # Handle string literals outside tags or inside braces
        if c == '"' and not in_single_quote and not in_backtick:
            in_double_quote = not in_double_quote
            i += 1
            continue
        if c == "'" and not in_double_quote and not in_backtick:
            in_single_quote = not in_single_quote
            i += 1
            continue
        if c == '`' and not in_double_quote and not in_single_quote:
            in_backtick = not in_backtick
            i += 1
            continue
            
        if in_double_quote or in_single_quote or in_backtick:
            i += 1
            continue
            
        # Handle braces { }
        if c == '{':
            depth = 1
            j = i + 1
            sub_in_double_quote = False
            sub_in_single_quote = False
            sub_in_backtick = False
            
            while j < n and depth > 0:
                sc = code[j]
                if sc == '"' and not sub_in_single_quote and not sub_in_backtick:
                    sub_in_double_quote = not sub_in_double_quote
                elif sc == "'" and not sub_in_double_quote and not sub_in_backtick:
                    sub_in_single_quote = not sub_in_single_quote
                elif sc == '`' and not sub_in_double_quote and not sub_in_single_quote:
                    sub_in_backtick = not sub_in_backtick
                
                if not (sub_in_double_quote or sub_in_single_quote or sub_in_backtick):
                    if sc == '{':
                        depth += 1
                    elif sc == '}':
                        depth -= 1
                j += 1
                
            if depth == 0:
                brace_content = code[i+1:j-1]
                if not re.search(r"<[a-zA-Z_/>]", brace_content):
                    i = j
                    continue
                else:
                    i += 1
                    continue
            else:
                i += 1
                continue
            
        # Detect tag boundaries
        if c == '<':
            if i + 1 < n:
                next_c = code[i+1]
                if next_c == '>':
                    tags.append(("Fragment", False, False))
                    i += 2
                    continue
                elif next_c == '/' and i + 2 < n and code[i+2] == '>':
                    tags.append(("Fragment", True, False))
                    i += 3
                    continue
                    
                is_closing = (next_c == '/')
                start_name_idx = i + 2 if is_closing else i + 1
                
                if start_name_idx < n and (code[start_name_idx].isalpha() or code[start_name_idx] == '_'):
                    tag_buffer = ""
                    tag_i = start_name_idx
                    
                    # Extract tag name
                    while tag_i < n:
                        tc = code[tag_i]
                        if tc.isalnum() or tc in '._-':
                            tag_buffer += tc
                            tag_i += 1
                        else:
                            break
                            
                    # Parse attributes
                    tag_brace_depth = 0
                    tag_in_double_quote = False
                    tag_in_single_quote = False
                    tag_in_backtick = False
                    self_closing = False
                    
                    while tag_i < n:
                        tc = code[tag_i]
                        
                        if tc == '"' and not tag_in_single_quote and not tag_in_backtick:
                            tag_in_double_quote = not tag_in_double_quote
                        elif tc == "'" and not tag_in_double_quote and not tag_in_backtick:
                            tag_in_single_quote = not tag_in_single_quote
                        elif tc == '`' and not tag_in_double_quote and not tag_in_single_quote:
                            tag_in_backtick = not tag_in_backtick
                            
                        if tag_in_double_quote or tag_in_single_quote or tag_in_backtick:
                            tag_i += 1
                            continue
                            
                        if tc == '{':
                            tag_brace_depth += 1
                        elif tc == '}':
                            if tag_brace_depth > 0:
                                tag_brace_depth -= 1
                                
                        if tag_brace_depth > 0:
                            tag_i += 1
                            continue
                            
                        if tc == '/':
                            peek_i = tag_i + 1
                            while peek_i < n and code[peek_i].isspace():
                                peek_i += 1
                            if peek_i < n and code[peek_i] == '>':
                                self_closing = True
                                tag_i = peek_i
                                break
                        elif tc == '>':
                            break
                            
                        tag_i += 1
                        
                    if tag_i < n and code[tag_i] == '>':
                        tags.append((tag_buffer, is_closing, self_closing))
                        i = tag_i + 1
                        continue
        i += 1
        
    return tags

def _check_tags_balanced(code: str) -> list[str]:
    """Helper method to check if JSX tags are balanced using a simple tag stack.
    
    Filters out comparison operator false positives by parsing tags with a
    state-machine tokenizer that ignores `<` and `>` inside JS expressions/braces.
    """
    issues = []
    matches = extract_jsx_tags(code)
    
    stack = []
    for clean_name, is_closing, self_closing in matches:
        if not is_valid_jsx_tag(clean_name):
            continue

        # If it's a self-closing tag (ends with /), skip pushing to stack
        if self_closing:
            continue

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
            stack.append(clean_name)
            
    while stack:
        top = stack.pop()
        issues.append(f"Unbalanced opening tag: <{top}> with no matching closing tag.")
        
    return issues

