"""Seed sample DSA problems into the coding_problems table."""

import json
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:Rohan%40123@localhost:5432/ProctoAi",
)


PROBLEMS = [
    {
        "title": "Two Sum",
        "description": (
            "Given an array of integers nums and an integer target, return the indices of the two "
            "numbers such that they add up to target.\n\n"
            "You may assume that each input would have exactly one solution, and you may not use "
            "the same element twice.\n\n"
            "Input format:\n"
            "  Line 1: space-separated integers (the array)\n"
            "  Line 2: integer (the target)\n\n"
            "Output: two space-separated indices (i j with i < j)."
        ),
        "difficulty": "easy",
        "starter_code": {
            "python": (
                "import sys\n\n"
                "def two_sum(nums, target):\n"
                "    # TODO: return [i, j] such that nums[i] + nums[j] == target\n"
                "    pass\n\n"
                "if __name__ == '__main__':\n"
                "    nums = list(map(int, input().split()))\n"
                "    target = int(input())\n"
                "    res = two_sum(nums, target)\n"
                "    print(res[0], res[1])\n"
            ),
            "javascript": (
                "function twoSum(nums, target) {\n"
                "  // TODO\n"
                "}\n\n"
                "const lines = require('fs').readFileSync(0, 'utf-8').trim().split('\\n');\n"
                "const nums = lines[0].split(' ').map(Number);\n"
                "const target = parseInt(lines[1]);\n"
                "const r = twoSum(nums, target);\n"
                "console.log(r[0] + ' ' + r[1]);\n"
            ),
        },
        "constraints": "2 <= nums.length <= 10^4 ; -10^9 <= nums[i] <= 10^9 ; -10^9 <= target <= 10^9",
        "tags": ["array", "hash-table"],
        "time_limit_ms": 2000,
        "memory_limit_kb": 256000,
        "test_cases": [
            {"input": "2 7 11 15\n9", "expected": "0 1", "is_sample": True},
            {"input": "3 2 4\n6", "expected": "1 2", "is_sample": True},
            {"input": "3 3\n6", "expected": "0 1", "is_sample": False},
            {"input": "-1 -2 -3 -4 -5\n-8", "expected": "2 4", "is_sample": False},
        ],
    },
    {
        "title": "Reverse a String",
        "description": (
            "Given a string s, return the string reversed.\n\n"
            "Input: a single line containing the string.\n"
            "Output: the reversed string on one line."
        ),
        "difficulty": "easy",
        "starter_code": {
            "python": (
                "def reverse_string(s):\n"
                "    # TODO\n"
                "    return s\n\n"
                "if __name__ == '__main__':\n"
                "    s = input()\n"
                "    print(reverse_string(s))\n"
            ),
            "javascript": (
                "function reverseString(s) {\n"
                "  // TODO\n"
                "  return s;\n"
                "}\n\n"
                "const s = require('fs').readFileSync(0, 'utf-8').trim();\n"
                "console.log(reverseString(s));\n"
            ),
        },
        "constraints": "1 <= s.length <= 10^5",
        "tags": ["string", "two-pointers"],
        "time_limit_ms": 1000,
        "memory_limit_kb": 128000,
        "test_cases": [
            {"input": "hello", "expected": "olleh", "is_sample": True},
            {"input": "ProctoAI", "expected": "IAotcorP", "is_sample": True},
            {"input": "a", "expected": "a", "is_sample": False},
            {"input": "abcdef", "expected": "fedcba", "is_sample": False},
        ],
    },
    {
        "title": "FizzBuzz",
        "description": (
            "Given an integer n, print the FizzBuzz sequence from 1 to n on one line "
            "separated by single spaces.\n\n"
            "Rules:\n"
            "  - Multiples of both 3 and 5 -> FizzBuzz\n"
            "  - Multiples of 3 only       -> Fizz\n"
            "  - Multiples of 5 only       -> Buzz\n"
            "  - Otherwise                 -> the number itself\n\n"
            "Input: a single integer n.\n"
            "Output: the sequence on one line, space-separated."
        ),
        "difficulty": "easy",
        "starter_code": {
            "python": (
                "def fizzbuzz(n):\n"
                "    # TODO: return list of strings\n"
                "    return []\n\n"
                "if __name__ == '__main__':\n"
                "    n = int(input())\n"
                "    print(' '.join(fizzbuzz(n)))\n"
            ),
            "javascript": (
                "function fizzbuzz(n) {\n"
                "  // TODO\n"
                "  return [];\n"
                "}\n\n"
                "const n = parseInt(require('fs').readFileSync(0, 'utf-8').trim());\n"
                "console.log(fizzbuzz(n).join(' '));\n"
            ),
        },
        "constraints": "1 <= n <= 1000",
        "tags": ["math", "string", "warmup"],
        "time_limit_ms": 1000,
        "memory_limit_kb": 64000,
        "test_cases": [
            {"input": "5", "expected": "1 2 Fizz 4 Buzz", "is_sample": True},
            {"input": "15", "expected": "1 2 Fizz 4 Buzz Fizz 7 8 Fizz Buzz 11 Fizz 13 14 FizzBuzz", "is_sample": True},
            {"input": "1", "expected": "1", "is_sample": False},
            {"input": "3", "expected": "1 2 Fizz", "is_sample": False},
        ],
    },
]


def main():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)

    inserted = 0
    for p in PROBLEMS:
        cur.execute(
            "SELECT id FROM coding_problems WHERE title = %s LIMIT 1",
            (p["title"],),
        )
        existing = cur.fetchone()
        if existing:
            print(f"  [skip] {p['title']} (id={existing['id']})")
            continue

        cur.execute(
            """
            INSERT INTO coding_problems
              (title, description, difficulty, starter_code, constraints, tags,
               time_limit_ms, memory_limit_kb, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            RETURNING id
            """,
            (
                p["title"],
                p["description"],
                p["difficulty"],
                json.dumps(p["starter_code"]),
                p["constraints"],
                json.dumps(p["tags"]),
                p["time_limit_ms"],
                p["memory_limit_kb"],
            ),
        )
        problem_id = cur.fetchone()["id"]

        for i, tc in enumerate(p["test_cases"]):
            cur.execute(
                """
                INSERT INTO coding_testcases
                  (problem_id, input_data, expected_output, is_sample, weight, order_index)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    problem_id,
                    tc["input"],
                    tc["expected"],
                    tc["is_sample"],
                    1.0,
                    i,
                ),
            )

        inserted += 1
        print(f"  [ok]   {p['title']} (id={problem_id}, {len(p['test_cases'])} test cases)")

    conn.commit()
    cur.close()
    conn.close()
    print(f"\nDone. Seeded {inserted} new problems.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
