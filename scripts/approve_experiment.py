"""Record explicit human approval for an immutable experiment specification."""
import argparse, json
from pathlib import Path
from research_engine.experiments import approve_experiment

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--approved-by", required=True)
    parser.add_argument("--rationale", required=True)
    args = parser.parse_args()
    result = approve_experiment(experiment_root=args.root, experiment_id=args.experiment_id,
                                approved_by=args.approved_by, rationale=args.rationale)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__": main()
