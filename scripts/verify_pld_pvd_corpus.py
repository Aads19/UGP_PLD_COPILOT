from __future__ import annotations

import argparse
import csv
import math
import random
import re
import sys
from pathlib import Path


csv.field_size_limit(10**8)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


PLD_KW = re.compile(
    r"pulsed laser deposition|(?<![a-z])pld(?![a-z])|laser ablation deposition|"
    r"krf excimer|ablation plume|plad|rpld|pulsed laser ablation",
    re.I,
)
PVD_KW = re.compile(
    r"sputtering|magnetron sputtering|molecular beam epitaxy|(?<![a-z])mbe(?![a-z])|"
    r"physical vap[ou]r deposition|(?<![a-z])pvd(?![a-z])|evaporation deposit|"
    r"hipims|high.power impulse magnetron sputtering|ipvd|ibad|ion beam assisted deposition|"
    r"thermal evaporation|electron beam evaporation|e.beam evaporation",
    re.I,
)
ALD_KW = re.compile(
    r"atomic layer deposition|(?<![a-z])ald(?![a-z])|atomic layer epitaxy|"
    r"(?<![a-z])ale(?![a-z])|half.reaction|self.limiting growth",
    re.I,
)
CVD_KW = re.compile(
    r"chemical vap[ou]r deposition|(?<![a-z])cvd(?![a-z])|mocvd|pecvd|lpcvd|"
    r"metalorganic.*deposition|organometallic.*deposition",
    re.I,
)
OTHER_KW = re.compile(
    r"sol.gel|chemical solution deposition|electrodeposition|spray pyrolysis|"
    r"inkjet|screen.print|dip.coat|spin.coat|spin.cast|doctor.blade|chemical bath deposition",
    re.I,
)
CHARACTERISATION_HINT_KW = re.compile(r"deposition|film|coating|layer|thin film", re.I)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Load ACS/AIP/Elsevier paragraph CSVs, deduplicate to unique papers, "
            "sample 100 papers, classify them, and run PLD/PVD focus tests."
        )
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path(r"C:\UGP - SHIKHA MISRA\New folder\UGP DATABASE"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--use-all", action="store_true")
    return parser.parse_args()


def normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def load_unique_papers(input_dir: Path) -> list[dict[str, str]]:
    papers_by_doi: dict[str, dict[str, str]] = {}
    filenames = ["acs_para.csv", "aip_para.csv", "els_para.csv"]

    for filename in filenames:
        path = input_dir / filename
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                doi_raw = clean_text(row.get("doi"))
                title = clean_text(row.get("title"))
                abstract = clean_text(row.get("abstract"))

                if not doi_raw or not title or not abstract:
                    continue

                doi = doi_raw.lower()
                if doi in papers_by_doi:
                    continue

                papers_by_doi[doi] = {"doi": doi, "title": title, "abstract": abstract}

    return list(papers_by_doi.values())


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def classify(paper: dict[str, str]) -> str:
    text = f"{paper['title']} {paper['abstract']}".lower()
    if PLD_KW.search(text):
        return "PLD"
    if PVD_KW.search(text):
        return "PVD"
    if ALD_KW.search(text):
        return "ALD"
    if CVD_KW.search(text):
        return "CVD"
    if OTHER_KW.search(text):
        return "OTHER_DEPOSITION"
    if CHARACTERISATION_HINT_KW.search(text):
        return "CHARACTERISATION_ONLY"
    return "IRRELEVANT"


def label_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        label = row["label"]
        counts[label] = counts.get(label, 0) + 1
    return counts


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    papers = load_unique_papers(args.input_dir)
    print(f"Total unique papers available: {len(papers)}")

    if args.sample_size <= 0:
        raise ValueError("--sample-size must be a positive integer.")
    if (not args.use_all) and len(papers) < args.sample_size:
        raise ValueError(f"Need at least {args.sample_size} papers to sample, found {len(papers)}.")

    if args.use_all:
        sample = list(papers)
        output_stem = "all_papers"
    else:
        sample = random.Random(42).sample(papers, args.sample_size)
        output_stem = f"{args.sample_size}_papers"

    sample_path = args.output_dir / f"sample_{output_stem}.csv"
    write_csv(sample_path, sample, ["doi", "title", "abstract"])

    if args.use_all:
        print(f"\n========== FULL CORPUS ({len(sample)} PAPERS) ==========")
    else:
        print(f"\n========== RANDOM SAMPLE ({args.sample_size} PAPERS) ==========")

    if len(sample) <= 200:
        for paper in sample:
            print(f"{paper['doi']} | {paper['title']}")
    else:
        print("Skipping paper-by-paper console listing because the selection is large.")

    classified_sample: list[dict[str, str]] = []
    for paper in sample:
        row = dict(paper)
        row["label"] = classify(row)
        classified_sample.append(row)

    n = len(classified_sample)
    pld_pvd_count = sum(1 for row in classified_sample if row["label"] in {"PLD", "PVD"})
    p_hat = pld_pvd_count / n
    p_0 = 0.50

    z_stat = (p_hat - p_0) / math.sqrt(p_0 * (1 - p_0) / n)
    p_value = normal_cdf(z_stat)

    print("\n========== TEST 1: PLD/PVD FOCUS ==========")
    print(f"PLD/PVD count  : {pld_pvd_count} / {n}")
    print(f"Observed p-hat : {p_hat:.3f}")
    print(f"Z-statistic    : {z_stat:.4f}")
    print(f"p-value (left) : {p_value:.4f}")
    if p_value < 0.05:
        print("REJECT H0 - corpus is NOT sufficiently PLD/PVD focused.")
    else:
        print("FAIL TO REJECT H0 - corpus appears sufficiently PLD/PVD focused.")

    ci_low = p_hat - 1.96 * math.sqrt(p_hat * (1 - p_hat) / n)
    ci_high = p_hat + 1.96 * math.sqrt(p_hat * (1 - p_hat) / n)
    print(f"95% CI         : ({ci_low:.3f}, {ci_high:.3f})")

    ald_count = sum(1 for row in classified_sample if row["label"] == "ALD")
    p_ald_hat = ald_count / n
    p_ald_0 = 0.10

    z_ald = (p_ald_hat - p_ald_0) / math.sqrt(p_ald_0 * (1 - p_ald_0) / n)
    pv_ald = 1 - normal_cdf(z_ald)

    print("\n========== TEST 2: ALD CONTAMINATION ==========")
    print(f"ALD count       : {ald_count} / {n}")
    print(f"Observed p-hat  : {p_ald_hat:.3f}")
    print(f"Z-statistic     : {z_ald:.4f}")
    print(f"p-value (right) : {pv_ald:.4f}")
    if pv_ald < 0.05:
        print("REJECT H0 - ALD contamination is SIGNIFICANT. Consider filtering.")
    else:
        print("FAIL TO REJECT H0 - ALD contamination is within acceptable range.")

    counts = label_counts(classified_sample)
    ordered_labels = [
        "PLD",
        "PVD",
        "ALD",
        "CVD",
        "OTHER_DEPOSITION",
        "CHARACTERISATION_ONLY",
        "IRRELEVANT",
    ]
    print("\n========== CLASSIFICATION SUMMARY ==========")
    for label in ordered_labels:
        print(f"{label:22} {counts.get(label, 0)}")

    other_irrelevant = sum(
        1
        for row in classified_sample
        if row["label"] in {"OTHER_DEPOSITION", "CHARACTERISATION_ONLY", "IRRELEVANT"}
    )
    print(f"\nOn-topic  (PLD+PVD) : {pld_pvd_count}")
    print(f"ALD (contamination) : {ald_count}")
    print(f"CVD                 : {counts.get('CVD', 0)}")
    print(f"Other / Irrelevant  : {other_irrelevant}")

    classified_path = args.output_dir / f"classified_sample_{output_stem}.csv"
    write_csv(classified_path, classified_sample, ["doi", "title", "abstract", "label"])
    print(f"\nSaved: {sample_path}")
    print(f"Saved: {classified_path}")


if __name__ == "__main__":
    main()
