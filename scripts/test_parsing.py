#!/usr/bin/env python3
"""Simple test to verify the argument parsing fix."""

import sys
sys.path.insert(0, '/root/UTSA-SOYOUDU/PharmAgent/purple_agent/src')

from agent import Agent

def test_argument_parsing():
    """Test that the agent now parses arguments correctly."""

    # Create agent instance to access parsing method
    agent = Agent()

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
            result = agent._parse_tool_args(args_str)
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