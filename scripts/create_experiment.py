"""Create a reproducible experiment specification from a registered dataset."""
import argparse, json
from pathlib import Path
from research_engine.experiments import create_experiment

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--strategy-id", required=True)
    parser.add_argument("--strategy-version", required=True)
    parser.add_argument("--parameters-json", required=True)
    parser.add_argument("--cost-model-json", required=True)
    parser.add_argument("--execution-model-json", required=True)
    parser.add_argument("--code-revision", required=True)
    parser.add_argument("--hypothesis", default="")
    args = parser.parse_args()
    result = create_experiment(registry_path=args.registry, experiment_root=args.root,
      dataset_id=args.dataset_id, strategy_id=args.strategy_id, strategy_version=args.strategy_version,
      parameters=json.loads(args.parameters_json), cost_model=json.loads(args.cost_model_json),
      execution_model=json.loads(args.execution_model_json), code_revision=args.code_revision,
      hypothesis=args.hypothesis)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__": main()
