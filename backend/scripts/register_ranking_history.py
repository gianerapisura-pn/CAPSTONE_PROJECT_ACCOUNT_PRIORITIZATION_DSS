"""Register fixed study history without rerunning analytics or modifying publications."""
import argparse

from app.db.session import SessionLocal
from app.services.ranking_history import seed_ranking_history


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, help="Private, hash-verified final analytical ZIP")
    parser.add_argument("--apply", action="store_true", help="Commit evidence; otherwise verify and roll back")
    args = parser.parse_args()
    with SessionLocal() as db:
        count = seed_ranking_history(db, args.package)
        db.flush()
        if args.apply:
            db.commit()
        else:
            db.rollback()
    print(f"{'Registered' if args.apply else 'Verified without committing'} {count} fixed study ranking records.")


if __name__ == "__main__":
    main()
