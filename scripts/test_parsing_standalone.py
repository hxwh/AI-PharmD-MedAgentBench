#!/usr/bin/env python3
"""Standalone test for argument parsing logic."""

import json
import re

def _parse_balanced_json(s: str, quote_char: str) -> tuple:
    """Parse JSON with balanced braces."""
    if not s or s[0] not in ('{', '['):
        return None, 0

    open_char = s[0]
    close_char = '}' if open_char == '{' else ']'

    depth = 0
    in_string = False
    inner_quote = None
    i = 0

    while i < len(s):
        c = s[i]

        if c in ('"', "'") and (i == 0 or s[i-1] != '\\'):
            if not in_string:
                in_string = True
                inner_quote = c
            elif c == inner_quote:
                in_string = False
                inner_quote = None
        elif not in_string:
            if c == open_char:
                depth += 1
            elif c == close_char:
                depth -= 1
                if depth == 0:
                    json_str = s[:i + 1]
                    end_idx = i + 1
                    if quote_char and end_idx < len(s) and s[end_idx] == quote_char:
                        end_idx += 1
                    return json_str, end_idx
        i += 1

    return None, 0

def _parse_tool_args(args_str: str) -> dict:
    """Parse tool arguments from string."""
    if not args_str:
        return {}

    args = {}
    i = 0

    while i < len(args_str):
        # Skip whitespace and commas
        while i < len(args_str) and args_str[i] in ' \t\n,':
            i += 1
        if i >= len(args_str):
            break

        # Look for key=
        key_match = re.match(r'(\w+)\s*=\s*', args_str[i:])
        if not key_match:
            i += 1
            continue

        key = key_match.group(1)
        i += key_match.end()

        if i >= len(args_str):
            break

        # Parse value
        if args_str[i] in ('"', "'"):
            quote_char = args_str[i]
            i += 1

            if i >= len(args_str):
                break

            # Check for JSON
            if args_str[i] in ('{', '['):
                value, end_idx = _parse_balanced_json(args_str[i:], quote_char)
                if value is not None:
                    try:
                        args[key] = json.loads(value)
                    except json.JSONDecodeError:
                        args[key] = value
                    i += end_idx
                    continue

            # Simple string value
            value_start = i
            while i < len(args_str):
                if args_str[i] == quote_char and (i == value_start or args_str[i-1] != '\\'):
                    args[key] = args_str[value_start:i]
                    i += 1
                    break
                i += 1

        elif args_str[i] in ('{', '['):
            value, end_idx = _parse_balanced_json(args_str[i:], None)
            if value is not None:
                try:
                    args[key] = json.loads(value)
                except json.JSONDecodeError:
                    args[key] = value
                i += end_idx
                continue

        elif args_str[i].isdigit() or (args_str[i] == '-' and i + 1 < len(args_str) and args_str[i+1].isdigit()):
            num_match = re.match(r'-?\d+\.?\d*', args_str[i:])
            if num_match:
                num_str = num_match.group(0)
                args[key] = float(num_str) if '.' in num_str else int(num_str)
                i += num_match.end()
        else:
            # Unquoted string values
            value_start = i
            while i < len(args_str) and args_str[i] not in ',)':
                i += 1
            args[key] = args_str[value_start:i].strip()

    return args

def test_argument_parsing():
    """Test that the argument parsing works correctly."""

    import re

    # Test cases for argument parsing
    test_cases = [
        # Test dict parsing (should work now with double quotes)
        ('note={"text": "test comment"}', {'note': {'text': 'test comment'}}),
        ('subject={"reference": "Patient/123"}', {'subject': {'reference': 'Patient/123'}}),
        ('code={"coding": [{"system": "url", "code": "value", "display": "name"}]}',
         {'code': {'coding': [{'system': 'url', 'code': 'value', 'display': 'name'}]}}),
        # Test string parsing (should still work)
        ('patient="Patient/123"', {'patient': 'Patient/123'}),
        ('priority="stat"', {'priority': 'stat'}),
    ]

    success = True
    for args_str, expected in test_cases:
        try:
            result = _parse_tool_args(args_str)
            if result == expected:
                print(f"✅ PASS: {args_str} -> {result}")
            else:
                print(f"❌ FAIL: {args_str}")
                print(f"   Expected: {expected}")
                print(f"   Got:      {result}")
                success = False
        except Exception as e:
            print(f"❌ ERROR: {args_str} -> {e}")
            success = False

    return success

if __name__ == "__main__":
    print("Testing argument parsing fixes...")
    success = test_argument_parsing()
    print(f"\nOverall result: {'SUCCESS' if success else 'FAILED'}")
    exit(0 if success else 1)