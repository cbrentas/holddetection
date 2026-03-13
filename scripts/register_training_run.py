import argparse
import json
import sys
import os

# Add the project root to python path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.db.models import Dataset, TrainingRun, Model, Artifact, ArtifactType

def main():
    parser = argparse.ArgumentParser(description="Register an ML training run")
    parser.add_argument("json_file", help="Path to JSON file with training run details")
    args = parser.parse_args()

    with open(args.json_file, 'r') as f:
        data = json.load(f)

    db = SessionLocal()
    try:
        # Find or create dataset
        dataset_info = data.get("dataset")
        dataset_id = None
        if dataset_info:
            dataset = db.query(Dataset).filter(
                Dataset.name == dataset_info["name"],
                Dataset.version == dataset_info["version"]
            ).first()
            if not dataset:
                dataset = Dataset(
                    name=dataset_info["name"],
                    version=dataset_info["version"],
                    storage_uri=dataset_info.get("storage_uri", "")
                )
                db.add(dataset)
                db.flush()
            dataset_id = dataset.id

        # Create Training Run
        run_info = data.get("training_run", {})
        training_run = TrainingRun(
            dataset_id=dataset_id,
            status="succeeded",  # default to succeeded if registering past run
            hyperparams=run_info.get("hyperparams", {}),
            metrics=run_info.get("metrics", {})
        )
        db.add(training_run)
        db.flush()

        # Add Artifacts
        artifacts_info = data.get("artifacts", [])
        for art in artifacts_info:
            artifact = Artifact(
                training_run_id=training_run.id,
                type=ArtifactType(art["type"]),
                uri=art["uri"]
            )
            db.add(artifact)

        # Optional linked model
        model_info = data.get("model")
        if model_info:
            model = Model(
                name=model_info["name"],
                version=model_info["version"],
                weights_uri=model_info["weights_uri"],
                training_run_id=training_run.id
            )
            db.add(model)

        db.commit()
        print(f"Training run registered with ID: {training_run.id}")
        if model_info:
            print(f"Linked model '{model_info['name']}' version '{model_info['version']}' registered.")

    except Exception as e:
        db.rollback()
        print(f"Error registering training run: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
