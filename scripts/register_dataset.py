"""Validate and register a canonical dataset in an append-only JSON registry."""
import argparse, json
from pathlib import Path
from research_engine.dataset_registry import register_dataset

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(register_dataset(args.csv, args.manifest, args.registry), ensure_ascii=False, indent=2))

if __name__ == "__main__": main()
