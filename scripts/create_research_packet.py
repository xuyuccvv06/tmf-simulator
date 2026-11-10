"""Validate researcher/reviewer artifacts and create a Python handoff packet."""
import argparse, json
from pathlib import Path
from research_engine.research_workflow import create_research_packet

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--experiment-spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    packet = create_research_packet(read_json(args.proposal), read_json(args.review), read_json(args.experiment_spec))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(packet, ensure_ascii=False, indent=2))

if __name__ == "__main__": main()