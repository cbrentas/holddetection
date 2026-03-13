import argparse
import json
import sys
import os

# Add the project root to python path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.db.models import Dataset

def main():
    parser = argparse.ArgumentParser(description="Register a new dataset version")
    parser.add_argument("json_file", help="Path to JSON file with dataset details")
    args = parser.parse_args()

    with open(args.json_file, 'r') as f:
        data = json.load(f)

    db = SessionLocal()
    try:
        dataset = Dataset(
            name=data["name"],
            version=data["version"],
            storage_uri=data["storage_uri"],
            meta=data.get("meta", {})
        )
        db.add(dataset)
        db.commit()
        print(f"Dataset {dataset.name} version {dataset.version} registered with ID: {dataset.id}")
    except Exception as e:
        db.rollback()
        print(f"Error registering dataset: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
