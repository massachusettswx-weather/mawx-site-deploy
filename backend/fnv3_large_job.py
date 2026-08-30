from fnv3_large.run import (
    run_fnv3_large,
)


def main():
    print("=" * 70)
    print("MASSACHUSETTSWX FNV3-L OPERATIONAL JOB")
    print("=" * 70)

    result = run_fnv3_large()

    print()
    print("FNV3-L RESULT:")
    print(result)


if __name__ == "__main__":
    main()
