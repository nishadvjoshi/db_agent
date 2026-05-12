import argparse
from app.crawler import crawl_database

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--include", nargs="*", default=None, help="Schemas to include")
    ap.add_argument("--exclude", nargs="*", default=None, help="Schemas to exclude")
    args = ap.parse_args()

    run_id = crawl_database(include_schemas=args.include, exclude_schemas=args.exclude)
    print(run_id)

if __name__ == "__main__":
    main()
