"""
Kaggle-ready sentence splitter for the curated PLD paragraph CSV.

Expected input columns:
source, doi, selection_group, score, title, abstract, paragraph_index, paragraph

Example Kaggle usage:
    python kaggle_sentence_split_pld.py \
        --input /kaggle/input/YOUR_DATASET/pld_final_500_paragraphs_flat.csv \
        --output /kaggle/working/pld_final_500_sentences.csv

The splitter uses regex with placeholders to avoid breaking scientific text at
common false boundaries such as 650 Â°C, decimals, formulas, abbreviations, and
citation-like references.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


DEFAULT_INPUT = "/kaggle/input/pld-final-500/pld_final_500_paragraphs_flat.csv"
DEFAULT_OUTPUT = "/kaggle/working/pld_final_500_sentences.csv"


ABBREVIATIONS = (
    "Fig.",
    "Figs.",
    "Eq.",
    "Eqs.",
    "Ref.",
    "Refs.",
    "No.",
    "Nos.",
    "Dr.",
    "Prof.",
    "et al.",
    "i.e.",
    "e.g.",
    "vs.",
    "cf.",
    "ca.",
    "approx.",
)


def normalize_text(text: str | None) -> str:
    """Normalize common encoding artifacts without changing scientific meaning."""
    if text is None:
        return ""

    replacements = {
        "\ufeff": "",
        "\u00a0": " ",
        "Â°C": "°C",
        "Â°": "°",
        "â€‰": " ",
        "â€¯": " ",
        "âˆ’": "−",
        "â€“": "–",
        "â€”": "—",
        "â€˜": "'",
        "â€™": "'",
        "â€œ": '"',
        "â€": '"',
        "Ã—": "×",
        "Î¼": "μ",
        "Îº": "κ",
        "Î±": "α",
        "Î²": "β",
        "Î³": "γ",
        "Î´": "δ",
        "Îµ": "ε",
        "Î¸": "θ",
        "Î»": "λ",
        "Ï€": "π",
        "Ï�": "ρ",
        "Ïƒ": "σ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def protect_spans(text: str) -> tuple[str, dict[str, str]]:
    """Replace no-split spans with placeholders before sentence splitting."""
    protected: dict[str, str] = {}

    def store(match: re.Match[str]) -> str:
        key = f"§§PROTECTED_{len(protected)}§§"
        protected[key] = match.group(0)
        return key

    # Common abbreviations and scientific writing shortcuts.
    for abbr in ABBREVIATIONS:
        key = f"§§PROTECTED_{len(protected)}§§"
        protected[key] = abbr
        text = text.replace(abbr, key)

    # Decimal numbers and version-like values: 0.12, 3.4, 1.4863440.
    text = re.sub(r"(?<=\d)\.(?=\d)", lambda m: store(m), text)

    # DOI-like strings and URLs.
    text = re.sub(r"https?://\S+", store, text)
    text = re.sub(r"\b10\.\d{4,9}/\S+", store, text)

    # Temperatures/units such as 650 °C, 650 Â°C, 1.2 nm, 5 cm2 V−1 s−1.
    unit_pattern = (
        r"\b\d+(?:(?:§§PROTECTED_\d+§§)\d+)?\s*"
        r"(?:°C|Â°C|K|mTorr|Torr|Pa|mbar|nm|μm|um|cm|mm|eV|keV|V|kV|MV|A|mA|Hz|kHz|MHz|J|mJ|W|mW)"
        r"(?:\s*[−-]?\d+)?"
    )
    text = re.sub(unit_pattern, store, text)

    # Chemical formula fragments and alloy/composition expressions. This helps
    # preserve spans such as La2Zr2−x, La0.7Sr0.3MnO3, In0.53Ga0.47As, TiO2.
    formula_pattern = (
        r"\b(?:[A-Z][a-z]?\d*(?:§§PROTECTED_\d+§§\d+)?(?:[−+\-–]?[xyz])?){2,}"
        r"(?:\([^)]+\)\d*)?"
    )
    text = re.sub(formula_pattern, store, text)

    # Initials and short capitalized labels: A. B. Smith, Pt. etc. Keep this
    # conservative to avoid swallowing real sentences.
    text = re.sub(r"\b[A-Z]\.", store, text)

    # Citation-like bracket groups and simple reference runs.
    text = re.sub(r"\[[0-9,\s–\-]+\]", store, text)
    text = re.sub(r"\b\d+\s*[–-]\s*\d+\b", store, text)

    return text, protected


def restore_spans(text: str, protected: dict[str, str]) -> str:
    # Repeat until nested placeholders introduced by protection are restored.
    changed = True
    while changed:
        changed = False
        for key, value in protected.items():
            if key in text:
                text = text.replace(key, value)
                changed = True
    return text


def split_sentences(text: str) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []

    protected_text, protected = protect_spans(text)

    # Split on final punctuation followed by whitespace and a likely sentence
    # starter. This avoids splitting formulas/units that have been protected.
    parts = re.split(r"(?<=[.!?])\s+(?=(?:[A-Z0-9\"'(\[]|[Α-Ω]))", protected_text)

    sentences: list[str] = []
    for part in parts:
        sentence = restore_spans(part, protected)
        sentence = normalize_text(sentence)
        if sentence:
            sentences.append(sentence)

    return sentences


def split_csv(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8-sig", newline="") as infile, output_path.open(
        "w", encoding="utf-8", newline=""
    ) as outfile:
        reader = csv.DictReader(infile)
        if reader.fieldnames is None:
            raise ValueError(f"No CSV header found in {input_path}")

        required = {"source", "doi", "title", "abstract", "paragraph_index", "paragraph"}
        missing = required.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        fieldnames = [
            "source",
            "doi",
            "selection_group",
            "score",
            "title",
            "abstract",
            "paragraph_index",
            "sentence_index",
            "sentence",
        ]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        total_paragraphs = 0
        total_sentences = 0

        for row in reader:
            total_paragraphs += 1
            sentences = split_sentences(row.get("paragraph", ""))

            for sentence_index, sentence in enumerate(sentences, start=1):
                total_sentences += 1
                writer.writerow(
                    {
                        "source": normalize_text(row.get("source", "")),
                        "doi": normalize_text(row.get("doi", "")),
                        "selection_group": normalize_text(row.get("selection_group", "")),
                        "score": normalize_text(row.get("score", "")),
                        "title": normalize_text(row.get("title", "")),
                        "abstract": normalize_text(row.get("abstract", "")),
                        "paragraph_index": normalize_text(row.get("paragraph_index", "")),
                        "sentence_index": sentence_index,
                        "sentence": sentence,
                    }
                )

    print(f"Input paragraphs: {total_paragraphs}")
    print(f"Output sentences: {total_sentences}")
    print(f"Wrote: {output_path}")


def run_self_test() -> None:
    examples = [
        "The sample was annealed at 650 Â°C. XRD confirmed crystallinity.",
        "The composition was La2Zr2âˆ’xCexO7. It remained stable.",
        "The film thickness was 0.12 nm/cycle. Fig. 2 shows the result.",
        "La0.7Sr0.3MnO3 was grown by PLD. The oxygen pressure was 10 mTorr.",
        "The DOI is https://doi.org/10.1063/1.4863440. This should not split inside it.",
    ]
    for text in examples:
        print("\nTEXT:", text)
        for idx, sentence in enumerate(split_sentences(text), start=1):
            print(f"{idx}: {sentence}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split PLD paragraph CSV into sentence CSV.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input flat paragraph CSV path.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output sentence CSV path.")
    parser.add_argument("--self-test", action="store_true", help="Run sentence-split self-test examples.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.self_test:
        run_self_test()
        return

    split_csv(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()
