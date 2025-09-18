import argparse
import concurrent.futures
import glob
import os
from pathlib import Path

import requests


def ingest_file(filepath: str) -> bool:
    """Ingest a single file using requests instead of curl."""
    # Always use markdown as MIME type
    mime_type = "text/markdown"
    api_url = "http://10.10.10.22:8889/api/ingest"

    try:
        with open(filepath, "rb") as file:
            files = {"files": (Path(filepath).name, file, mime_type)}
            with requests.Session() as session:
                response = session.post(api_url, files=files)

                if response.status_code == 200:
                    return True
                return False
    except Exception:
        return False


def ingest_all_files(data_dir: str, file_pattern: str = "*.md", parallel: bool = True):
    """Ingest all files matching pattern in the given directory."""
    # Get list of all files matching the pattern
    files = glob.glob(os.path.join(data_dir, file_pattern))

    if not files:
        print(f"No files found matching '{file_pattern}' in {data_dir}")
        return

    print(f"Found {len(files)} files to ingest")

    success_count = 0
    failure_count = 0

    # Process files in parallel or sequentially
    if parallel and len(files) > 1:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_file = {executor.submit(ingest_file, f): f for f in files}
            for future in concurrent.futures.as_completed(future_to_file):
                try:
                    success = future.result()
                    if success:
                        success_count += 1
                    else:
                        failure_count += 1
                except Exception as e:
                    failure_count += 1
                    file = future_to_file[future]
                    print(f"Error processing {Path(file).name}: {e}")
    else:
        for filepath in files:
            success = ingest_file(filepath)
            if success:
                success_count += 1
            else:
                failure_count += 1

    # Print summary
    print("\n===== Ingestion Summary =====")
    print(f"Total files: {len(files)}")
    print(f"Successfully ingested: {success_count}")
    print(f"Failed: {failure_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest files into the API")
    parser.add_argument(
        "--dir",
        type=str,
        default="data/raw_data/",
        help="Directory containing files to ingest",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.md",
        help='File pattern to match (e.g., "*.md", "*.txt")',
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Process files sequentially instead of in parallel",
    )

    args = parser.parse_args()
    ingest_all_files(args.dir, args.pattern, not args.sequential)
