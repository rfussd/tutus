"""
Fine-tuning QLoRA para TUTUS con tus conversaciones.

Uso:
    python training/train.py --dataset training/conversations.jsonl --output training/lora_adapter

Requiere: pip install peft bitsandbytes accelerate datasets transformers torch
"""

import argparse
import json
import logging
import sys
from pathlib import Path

log = logging.getLogger("tutus.train")

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForSeq2Seq,
    Trainer,
    TrainingArguments,
)

MODEL_NAME = "Qwen/Qwen3-VL-8B"
DEFAULT_OUTPUT = Path(__file__).parent / "lora_adapter"


def format_prompt(instruction: str, response: str | None = None) -> str:
    if response:
        return f"""<|im_start|>user
{instruction}<|im_end|>
<|im_start|>assistant
{response}<|im_end|>"""
    else:
        return f"""<|im_start|>user
{instruction}<|im_end|>
<|im_start|>assistant"""


def main():
    parser = argparse.ArgumentParser(description="Fine-tune TUTUS con QLoRA")
    parser.add_argument("--dataset", type=str, required=True, help="JSONL con {instruction, response}")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--batch", type=int, default=2)
    parser.add_argument("--gradient_accum", type=int, default=4)
    parser.add_argument("--lora_r", type=int, default=16)
    parser.add_argument("--lora_alpha", type=int, default=32)
    parser.add_argument("--lora_dropout", type=float, default=0.05)
    parser.add_argument("--max_length", type=int, default=1024)
    parser.add_argument("--model", type=str, default=MODEL_NAME)
    args = parser.parse_args()

    if not Path(args.dataset).exists():
        log.error("Dataset no encontrado: %s", args.dataset)
        log.info("Ejecuta primero: python training/prepare_dataset.py")
        sys.exit(1)

    log.info("[1/5] Cargando dataset: %s", args.dataset)
    pairs = []
    with open(args.dataset, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                pairs.append(json.loads(line))

    if not pairs:
        log.warning("Dataset vacio. No hay nada que entrenar.")
        sys.exit(1)

    log.info("  %d pares instruction-response", len(pairs))

    texts = [format_prompt(p["instruction"], p["response"]) for p in pairs]
    dataset = Dataset.from_dict({"text": texts})

    log.info("[2/5] Cargando tokenizer: %s", args.model)
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def tokenize_fn(examples):
        full = tokenizer(
            examples["text"],
            truncation=True,
            max_length=args.max_length,
            padding="max_length",
        )

        labels = full["input_ids"].copy()
        for i, text in enumerate(examples["text"]):
            asst_pos = text.find("<|im_start|>assistant\n")
            if asst_pos != -1:
                instr_text = text[: asst_pos + len("<|im_start|>assistant\n")]
                instr_ids = tokenizer(instr_text, truncation=True, max_length=args.max_length)["input_ids"]
                labels[i][: len(instr_ids)] = [-100] * min(len(instr_ids), len(labels[i]))

        full["labels"] = labels
        return full

    dataset = dataset.map(tokenize_fn, batched=True, remove_columns=["text"])

    log.info("[3/5] Configurando QLoRA (4-bit quantization)")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    log.info("[4/5] Iniciando entrenamiento")
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=args.gradient_accum,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        fp16=False,
        bf16=True,
        logging_steps=10,
        save_strategy="epoch",
        save_total_limit=2,
        remove_unused_columns=False,
        report_to="none",
        dataloader_num_workers=0,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=DataCollatorForSeq2Seq(tokenizer, pad_to_multiple_of=8),
    )

    trainer.train()

    log.info("[5/5] Guardando adaptador LoRA en: %s", output_dir)
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    log.info("Fine-tuning completado!")
    log.info("Para usar: configura LORA_ADAPTER_PATH='%s' en config.py", output_dir)


if __name__ == "__main__":
    main()
