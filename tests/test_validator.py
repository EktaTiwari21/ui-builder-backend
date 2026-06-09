import pytest
from app.services.validator import validate

def test_validate_valid_code():
    """Test that a standard React/Tailwind component with valid syntax passes validation."""
    code = """
    import React from 'react';
    import { ArrowRight, User } from 'lucide-react';

    export function ProfileCard() {
        return (
            <div className="p-6 max-w-sm mx-auto bg-white rounded-xl shadow-md flex items-center space-x-4">
                <div className="flex-shrink-0">
                    <User className="h-12 w-12 text-slate-500" />
                </div>
                <div>
                    <div className="text-xl font-medium text-black">Chit Chat</div>
                    <p className="text-gray-500">You have a new message!</p>
                    <button className="flex items-center text-indigo-500 hover:text-indigo-600 font-semibold">
                        View profile <ArrowRight className="ml-1 h-4 w-4" />
                    </button>
                </div>
            </div>
        );
    }
    """
    result = validate(code)
    assert result.is_valid
    assert len(result.errors) == 0

def test_validate_missing_named_export():
    """Test that validation fails when no named export is provided."""
    code = """
    import React from 'react';
    function Card() {
        return <div className="p-4 bg-red-100">Simple Card</div>;
    }
    """
    result = validate(code)
    assert not result.is_valid
    assert any("named export" in err.lower() for err in result.errors)

def test_validate_dangerous_patterns():
    """Test that dangerous patterns (eval, dangerouslySetInnerHTML, document.write) are blocked."""
    # Check eval
    code_eval = """
    export function BadComponent() {
        return <div className="p-4" onClick={() => eval('console.log("bad")')}>Click me</div>;
    }
    """
    result_eval = validate(code_eval)
    assert not result_eval.is_valid
    assert any("eval()" in err for err in result_eval.errors)

    # Check dangerouslySetInnerHTML
    code_html = """
    export function InnerHTMLComponent({ userContent }) {
        return <div className="p-4" dangerouslySetInnerHTML={{ __html: userContent }} />;
    }
    """
    result_html = validate(code_html)
    assert not result_html.is_valid
    assert any("dangerouslySetInnerHTML" in err for err in result_html.errors)

    # Check document.write
    code_write = """
    export function DirectWriteComponent() {
        const handleClick = () => {
            document.write("Malicious Script");
        };
        return <button className="p-2 bg-blue-500" onClick={handleClick}>Write</button>;
    }
    """
    result_write = validate(code_write)
    assert not result_write.is_valid
    assert any("document.write" in err for err in result_write.errors)

def test_validate_missing_tailwind():
    """Test that validation fails when no Tailwind class definition is present."""
    code = """
    import React from 'react';
    export function PlainComponent() {
        return (
            <div>
                <h1>Standard Text</h1>
                <p>No Tailwind styles whatsoever</p>
            </div>
        );
    }
    """
    result = validate(code)
    assert not result.is_valid
    assert any("tailwind" in err.lower() for err in result.errors)

def test_validate_disallowed_imports():
    """Test that imports from packages other than react or lucide-react are rejected."""
    code = """
    import React from 'react';
    import _ from 'lodash';
    export function CustomCard() {
        return <div className="p-4">Custom Content</div>;
    }
    """
    result = validate(code)
    assert not result.is_valid
    assert any("unauthorized package" in err.lower() for err in result.errors)

def test_validate_unbalanced_tags():
    """Test that unbalanced or mismatched opening/closing JSX tags are flagged as errors."""
    code = """
    export function UnbalancedDemo() {
        return (
            <div className="flex">
                <span className="text-bold">Mismatched Closing Tag</div>
            </div>
        );
    }
    """
    result = validate(code)
    assert not result.is_valid
    assert any("mismatched tags" in err.lower() or "unbalanced" in err.lower() for err in result.errors)
