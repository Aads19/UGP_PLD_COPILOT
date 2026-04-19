import os
import json
import time
import random

import pandas as pd
from google import genai
from google.genai import types
from kaggle_secrets import UserSecretsClient


# =========================
# Kaggle Config
# =========================
INPUT_SOURCE_FILE = "/kaggle/input/your-uploaded-source/Highly_Relevant_PLD_PVD_Sentences_To_Classify.csv"
INPUT_PARTIAL_PROGRESS_FILE = "/kaggle/input/your-uploaded-partial/Highly_Relevant_Batch3_Classified.csv"
INPUT_EXISTING_MERGED_FILE = "/kaggle/input/your-uploaded-merged/Merged_Classified_Chunks_Progress_Filled.csv"

OUTPUT_DIR = "/kaggle/working/"

PROGRESS_FILE = os.path.join(OUTPUT_DIR, "Highly_Relevant_Batch3_Resumed_Progress.csv")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "Highly_Relevant_Batch3_Resumed_Classified.csv")
REMAINING_FILE = os.path.join(OUTPUT_DIR, "Highly_Relevant_Batch3_Resumed_Remaining.csv")
COMBINED_WITH_MERGED_FILE = os.path.join(
    OUTPUT_DIR, "Merged_Classified_Chunks_Progress_Filled_PLUS_HighlyRelevant.csv"
)

MODEL_NAME = "gemini-2.5-flash"

WINDOW_SIZE = 10
STRIDE = 7
BATCH_SIZE = 3
MAX_RETRIES = 4

SAFE_RPM = 850
SAFE_TPM = 850_000
SAFE_RPD_STOP = 9000
CHECKPOINT_EVERY = 25


# =========================
# Gemini / Kaggle setup
# =========================
try:
    user_secrets = UserSecretsClient()
    api_key = user_secrets.get_secret("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
except Exception as e:
    print("Please make sure you have added GEMINI_API_KEY to Kaggle Secrets.")
    raise e


# =========================
# Constants
# =========================
ALLOWED_TAGS = ["Background", "Synthesis", "Characterization", "Analysis"]
ALLOWED_TAGS_SET = set(ALLOWED_TAGS)


# =========================
# Scheduler
# =========================
class RequestScheduler:
    def __init__(self, rpm_limit=850, tpm_limit=850_000, rpd_limit=9000):
        self.min_interval = 60.0 / rpm_limit
        self.tpm_limit = tpm_limit
        self.rpd_limit = rpd_limit
        self.last_request_time = 0.0
        self.requests_made_today = 0
        self.minute_window_start = time.time()
        self.tokens_used_this_minute = 0

    def estimate_tokens(self, text: str) -> int:
        return max(1, int(len(text) / 4))

    def can_make_request(self):
        return self.requests_made_today < self.rpd_limit

    def wait_for_slot(self, estimated_tokens: int):
        now = time.time()

        if now - self.minute_window_start >= 60:
            self.minute_window_start = now
            self.tokens_used_this_minute = 0

        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            print(f"Waiting {wait_time:.2f}s to respect RPM...")
            time.sleep(wait_time)

        now = time.time()
        if now - self.minute_window_start >= 60:
            self.minute_window_start = now
            self.tokens_used_this_minute = 0

        if self.tokens_used_this_minute + estimated_tokens > self.tpm_limit:
            wait_time = max(0.0, 60 - (now - self.minute_window_start)) + 1
            print(
                f"Waiting {wait_time:.2f}s to respect TPM "
                f"({self.tokens_used_this_minute + estimated_tokens}/{self.tpm_limit})..."
            )
            time.sleep(wait_time)
            self.minute_window_start = time.time()
            self.tokens_used_this_minute = 0

    def record_request(self, estimated_tokens: int):
        self.last_request_time = time.time()
        self.tokens_used_this_minute += estimated_tokens
        self.requests_made_today += 1

    def reset_timing(self):
        self.last_request_time = 0.0
        self.minute_window_start = time.time()
        self.tokens_used_this_minute = 0


# =========================
# Helpers
# =========================
def is_retryable_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    retryable_markers = [
        "429",
        "resource_exhausted",
        "rate limit",
        "quota",
        "too many requests",
        "503",
        "unavailable",
        "high demand",
        "deadline exceeded",
        "internal",
    ]
    return any(marker in msg for marker in retryable_markers)


def normalize_tags(tags):
    if not isinstance(tags, list):
        raise ValueError("tags must be a list")

    cleaned = []
    seen = set()

    for tag in tags:
        if not isinstance(tag, str):
            continue
        tag = tag.strip()
        if tag in ALLOWED_TAGS_SET and tag not in seen:
            cleaned.append(tag)
            seen.add(tag)

    return cleaned


def parse_batch_response_text(response_text: str, expected_chunk_ids):
    parsed = json.loads(response_text)

    if not isinstance(parsed, dict) or "results" not in parsed:
        raise ValueError("Batch response must be a JSON object with a 'results' field")

    results = parsed["results"]
    if not isinstance(results, list):
        raise ValueError("'results' must be a list")

    parsed_results = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        chunk_id = item.get("chunk_id")
        tags = normalize_tags(item.get("tags", []))
        if isinstance(chunk_id, int):
            parsed_results[chunk_id] = tags

    missing = [cid for cid in expected_chunk_ids if cid not in parsed_results]
    if missing:
        raise ValueError(f"Missing chunk_id(s) in batch response: {missing}")

    return parsed_results


def build_batch_prompt(title: str, abstract: str, batch_rows):
    chunk_blocks = []
    for local_idx, row in enumerate(batch_rows):
        chunk_blocks.append(
            f"CHUNK_ID: {local_idx}\nTEXT:\n{str(row['text_chunk'])}"
        )

    chunks_text = "\n\n".join(chunk_blocks)

    return f"""
You are classifying text chunks from a Physical Vapor Deposition (PVD) or Pulsed Laser Deposition (PLD) research paper.

Task:
Perform STRICT multi-label classification for EACH chunk independently.
Return ALL labels that are clearly supported by each chunk.
More than one label may apply to a chunk.

Allowed labels only:
- Background: prior work, motivation, context, literature framing, problem statement
- Synthesis: deposition method, fabrication, processing parameters, preparation, growth conditions
- Characterization: measurement techniques, instruments, microscopy, spectroscopy, diffraction, composition/morphology testing
- Analysis: interpretation of results, comparison, trends, mechanisms, performance discussion, conclusions from data

Rules:
- Output valid JSON only.
- Output exactly one JSON object with this schema:
  {{
    "results": [
      {{"chunk_id": 0, "tags": ["Background", "Analysis"]}},
      {{"chunk_id": 1, "tags": ["Synthesis"]}}
    ]
  }}
- Every chunk_id must appear exactly once.
- Use only the allowed labels.
- Include every applicable label for each chunk.
- Classify each chunk independently.
- Do not include explanation, markdown, or extra text.

Paper Title: {title}
Abstract: {abstract}

Chunks:
{chunks_text}
""".strip()


def classify_batch(client, scheduler, title, abstract, batch_rows):
    prompt = build_batch_prompt(title, abstract, batch_rows)
    last_error = None

    estimated_input_tokens = scheduler.estimate_tokens(prompt)
    estimated_output_tokens = 100 * len(batch_rows)
    estimated_total_tokens = estimated_input_tokens + estimated_output_tokens
    expected_chunk_ids = list(range(len(batch_rows)))

    for attempt in range(MAX_RETRIES):
        if not scheduler.can_make_request():
            raise RuntimeError(
                f"Daily stop limit reached ({scheduler.requests_made_today}/{scheduler.rpd_limit})."
            )

        scheduler.wait_for_slot(estimated_total_tokens)

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )

            scheduler.record_request(estimated_total_tokens)
            return parse_batch_response_text(response.text, expected_chunk_ids)

        except Exception as e:
            last_error = e

            if is_retryable_error(e):
                wait_time = min(180, 15 * (2 ** attempt)) + random.uniform(0, 5)
                print(f"Retryable error: {e}")
                if attempt < MAX_RETRIES - 1:
                    print(f"Retrying after {wait_time:.1f}s...")
                    scheduler.reset_timing()
                    time.sleep(wait_time)
            else:
                wait_time = 5
                print(f"Non-retryable error: {e}")
                if attempt < MAX_RETRIES - 1:
                    print(f"Retrying after {wait_time}s...")
                    time.sleep(wait_time)

    raise last_error


def load_input_dataframe(input_file: str) -> pd.DataFrame:
    df = pd.read_csv(input_file)
    expected_cols = {"doi", "title", "abstract", "sentence"}
    if not expected_cols.issubset(set(df.columns)):
        raise ValueError("Input file must contain columns: doi, title, abstract, sentence")
    df = df[["doi", "title", "abstract", "sentence"]].copy()
    df = df[df["sentence"].astype(str).str.strip() != ""].reset_index(drop=True)
    return df


def build_chunks_from_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    chunk_rows = []
    grouped_papers = df.groupby("doi", sort=False)

    for doi, group in grouped_papers:
        title = str(group["title"].iloc[0])
        abstract = str(group["abstract"].iloc[0])
        sentences = group["sentence"].astype(str).tolist()

        print(f"Preparing DOI: {doi} | Sentences: {len(sentences)}")

        for i in range(0, len(sentences), STRIDE):
            chunk_sentences = sentences[i:i + WINDOW_SIZE]
            chunk_text = " ".join(chunk_sentences).strip()

            if not chunk_text:
                continue

            chunk_rows.append({
                "doi": doi,
                "title": title,
                "abstract": abstract,
                "chunk_start_idx": i,
                "text_chunk": chunk_text,
            })

    return pd.DataFrame(chunk_rows)


def save_checkpoint(processed_rows):
    if processed_rows:
        checkpoint_df = pd.DataFrame(processed_rows)
        checkpoint_df.to_csv(PROGRESS_FILE, index=False)
        checkpoint_df.to_csv(OUTPUT_FILE, index=False)
        print(f"Checkpoint saved: {PROGRESS_FILE}")


def update_combined_with_merged():
    if not os.path.exists(OUTPUT_FILE):
        return

    merged_df = pd.read_csv(INPUT_EXISTING_MERGED_FILE)
    current_df = pd.read_csv(OUTPUT_FILE)
    current_df = current_df[current_df["tags"].astype(str).str.contains("Error_API") == False].copy()
    combined_df = pd.concat([merged_df, current_df], ignore_index=True)
    combined_df = dedupe_chunk_rows(combined_df)
    combined_df.to_csv(COMBINED_WITH_MERGED_FILE, index=False)


def make_row_key(row):
    return (str(row["doi"]), int(row["chunk_start_idx"]))


def get_unprocessed_rows(df, processed_keys):
    mask = df.apply(lambda x: make_row_key(x) not in processed_keys, axis=1)
    return df[mask].copy()


def dedupe_chunk_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    work_df = df.copy()
    work_df["_doi_key"] = work_df["doi"].astype(str)
    work_df["_chunk_key"] = work_df["chunk_start_idx"].astype(int)
    work_df["_is_error"] = work_df["tags"].astype(str).str.contains("Error_API", na=False)
    work_df = work_df.sort_values(
        by=["_doi_key", "_chunk_key", "_is_error"],
        ascending=[True, True, True],
        kind="stable",
    )
    work_df = work_df.drop_duplicates(subset=["_doi_key", "_chunk_key"], keep="first")
    work_df = work_df.drop(columns=["_doi_key", "_chunk_key", "_is_error"])
    return work_df.reset_index(drop=True)


# =========================
# Main
# =========================
scheduler = RequestScheduler(
    rpm_limit=SAFE_RPM,
    tpm_limit=SAFE_TPM,
    rpd_limit=SAFE_RPD_STOP,
)

source_df = load_input_dataframe(INPUT_SOURCE_FILE)
existing_merged_dois = set(pd.read_csv(INPUT_EXISTING_MERGED_FILE)["doi"].astype(str).unique().tolist())

source_df = source_df[~source_df["doi"].astype(str).isin(existing_merged_dois)].reset_index(drop=True)
chunks_df = build_chunks_from_dataframe(source_df)
print(f"Total chunks prepared after excluding merged DOIs: {len(chunks_df)}")

processed_rows = []
processed_keys = set()
error_keys = set()

if os.path.exists(INPUT_PARTIAL_PROGRESS_FILE):
    partial_df = pd.read_csv(INPUT_PARTIAL_PROGRESS_FILE)
    partial_df = dedupe_chunk_rows(partial_df)
    good_df = partial_df[partial_df["tags"].astype(str).str.contains("Error_API") == False].copy()
    err_df = partial_df[partial_df["tags"].astype(str).str.contains("Error_API")].copy()

    processed_rows = good_df.to_dict("records")
    processed_keys = set(
        zip(
            good_df["doi"].astype(str),
            good_df["chunk_start_idx"].astype(int),
        )
    )
    error_keys = set(
        zip(
            err_df["doi"].astype(str),
            err_df["chunk_start_idx"].astype(int),
        )
    )

    print(f"Loaded partial progress: {len(good_df)} successful rows, {len(err_df)} Error_API rows to rerun")

grouped_chunks = chunks_df.groupby("doi", sort=False)
stop_run = False

for doi, paper_group in grouped_chunks:
    paper_rows = paper_group.to_dict("records")
    target_rows = []

    for row in paper_rows:
        key = make_row_key(row)
        if key in error_keys or key not in processed_keys:
            target_rows.append(row)

    if not target_rows:
        continue

    title = str(target_rows[0]["title"])
    abstract = str(target_rows[0]["abstract"])

    for start_idx in range(0, len(target_rows), BATCH_SIZE):
        batch_rows = target_rows[start_idx:start_idx + BATCH_SIZE]

        if scheduler.requests_made_today >= SAFE_RPD_STOP:
            print(f"Reached daily stop limit at {scheduler.requests_made_today} requests. Saving remaining chunks.")
            remaining_df = get_unprocessed_rows(chunks_df, processed_keys)
            remaining_df.to_csv(REMAINING_FILE, index=False)
            save_checkpoint(processed_rows)
            update_combined_with_merged()
            stop_run = True
            break

        try:
            batch_result = classify_batch(
                client=client,
                scheduler=scheduler,
                title=title,
                abstract=abstract,
                batch_rows=batch_rows,
            )

            for local_idx, row in enumerate(batch_rows):
                key = make_row_key(row)

                result_row = {
                    "doi": row["doi"],
                    "title": row["title"],
                    "chunk_start_idx": row["chunk_start_idx"],
                    "text_chunk": row["text_chunk"],
                    "tags": json.dumps({"tags": batch_result[local_idx]}, ensure_ascii=False),
                }

                processed_rows = [r for r in processed_rows if (str(r["doi"]), int(r["chunk_start_idx"])) != key]
                processed_rows.append(result_row)
                processed_keys.add(key)
                if key in error_keys:
                    error_keys.remove(key)

            print(
                f"Successfully processed chunks {len(processed_rows) - len(batch_rows) + 1}-{len(processed_rows)} "
                f"(requests used: {scheduler.requests_made_today}/{SAFE_RPD_STOP})"
            )

            if len(processed_rows) % CHECKPOINT_EVERY == 0:
                save_checkpoint(processed_rows)
                update_combined_with_merged()

        except RuntimeError as e:
            print(f"Stopping run: {e}")
            remaining_df = get_unprocessed_rows(chunks_df, processed_keys)
            remaining_df.to_csv(REMAINING_FILE, index=False)
            save_checkpoint(processed_rows)
            update_combined_with_merged()
            stop_run = True
            break

        except Exception as e:
            print(f"  -> FAILED after {MAX_RETRIES} attempts: {e}")

            for row in batch_rows:
                key = make_row_key(row)
                processed_rows = [r for r in processed_rows if (str(r["doi"]), int(r["chunk_start_idx"])) != key]
                processed_rows.append({
                    "doi": row["doi"],
                    "title": row["title"],
                    "chunk_start_idx": row["chunk_start_idx"],
                    "text_chunk": row["text_chunk"],
                    "tags": json.dumps({"tags": ["Error_API"]}, ensure_ascii=False),
                })
                if key not in processed_keys:
                    error_keys.add(key)

            if len(processed_rows) % CHECKPOINT_EVERY == 0:
                save_checkpoint(processed_rows)
                update_combined_with_merged()

    if stop_run:
        break

save_checkpoint(processed_rows)
update_combined_with_merged()

if not os.path.exists(REMAINING_FILE):
    print("No remaining chunks left to process.")
else:
    print(f"Remaining chunks saved to: {REMAINING_FILE}")

print("Run finished.")
