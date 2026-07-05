"""
Exporta conversaciones guardadas a JSONL y CSV para fine-tuning.
Uso: python training/prepare_dataset.py [--limit 1000]
"""

import argparse
import logging
from pathlib import Path

log = logging.getLogger("tutus.prepare_dataset")


def main():
    parser = argparse.ArgumentParser(description="Exportar conversaciones para fine-tuning")
    parser.add_argument("--limit", type=int, default=500, help="Max conversaciones a exportar")
    parser.add_argument("--output", type=str, default=None, help="Ruta de salida")
    args = parser.parse_args()

    from core.memory_signals import export_conversations_for_training

    result = export_conversations_for_training(output_path=args.output, limit=args.limit)
    log.info("Export result: %s", result)

    out_path = args.output or str(Path(__file__).parent / "conversations.jsonl")
    if Path(out_path).exists():
        count = sum(1 for _ in open(out_path, encoding="utf-8"))
        log.info("Total pares instruction-response: %d", count)


if __name__ == "__main__":
    main()
