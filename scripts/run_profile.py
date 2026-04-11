import argparse
from app.profiler import profile_run

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--schemas", nargs="*", default=None)
    args = ap.parse_args()
    profile_run(args.run_id, schemas=args.schemas)
    print("OK")

if __name__ == "__main__":
    main()
