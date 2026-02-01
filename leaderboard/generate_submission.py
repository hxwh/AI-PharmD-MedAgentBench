#!/usr/bin/env python3
"""
Generate submission files for the leaderboard
"""

import json
import os
import glob

def generate_submission():
    """Generate submission from latest assessment results"""

    # Find latest assessment result
    result_files = glob.glob('results/assessment_*.json')
    if not result_files:
        print("No assessment results found")
        return

    latest_file = max(result_files, key=os.path.getctime)

    with open(latest_file) as f:
        assessment = json.load(f)

    # Create submission
    submission = {
        'submission_id': assessment['submission_id'],
        'participant_id': assessment['participant_id'],
        'config': assessment['config'],
        'result': assessment['result'],
        'created_at': assessment['created_at']
    }

    # Save submission
    os.makedirs('submissions', exist_ok=True)
    submission_file = f'submissions/submission_{assessment["submission_id"]}.json'

    with open(submission_file, 'w') as f:
        json.dump(submission, f, indent=2)

    print(f"Submission created: {submission_file}")

if __name__ == '__main__':
    generate_submission()