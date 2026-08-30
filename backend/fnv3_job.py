from fnv3.run import (
    run_fnv3,
)


def main():
    print("=" * 70)
    print("MASSACHUSETTSWX FNV3 OPERATIONAL JOB")
    print("=" * 70)

    result = run_fnv3()

    print()
    print("FNV3 RESULT:")
    print(result)


if __name__ == "__main__":
    main()
