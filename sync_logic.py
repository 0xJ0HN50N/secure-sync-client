import os
import json
import hashlib
import time

CHUNK_SIZE = 64 * 1024           # 64 KB chunks
MANIFEST_FILE = "manifest.json"  # local record of what has already been synced
REMOTE_DIR = "remote_server"     # stand-in for the real remote server

def load_manifest():
    if os.path.exists(MANIFEST_FILE):
        with open(MANIFEST_FILE, "r") as f:
            return json.load(f)
    return {}

def save_manifest(manifest):
    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, indent=2)

def hash_file(path):
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK_SIZE), b""):
            sha256.update(block)
    return sha256.hexdigest()

def find_changed_files(watch_dir, manifest):
    changed = []
    for root, _, files in os.walk(watch_dir):
        for name in files:
            path = os.path.join(root, name)
            current_mtime = os.path.getmtime(path)
            record = manifest.get(path)
            if record and record.get("mtime") == current_mtime:
                continue  # unchanged since the last successful sync
            current_hash = hash_file(path)
            previous_hash = record.get("hash") if record else None
            if current_hash != previous_hash:
                changed.append((path, current_hash))
    return changed

def _server_receive_chunk(filename, chunk_index, data):
    chunk_path = os.path.join(REMOTE_DIR, f"{filename}.part{chunk_index}")
    with open(chunk_path, "wb") as out:
        out.write(data)
    return True  # ACK server confirms the chunk was received

def send_file(path, file_hash, manifest):
    # Chunks are always sent in order so resume only needs a count of how many have been acknowledged so far not a list of which ones.
    os.makedirs(REMOTE_DIR, exist_ok=True)
    filename = os.path.basename(path)
    progress_key = f"{path}:progress"
    chunks_acked = manifest.get(progress_key, 0)

    with open(path, "rb") as f:
        f.seek(chunks_acked * CHUNK_SIZE)  # skip straight past acknowledged chunks
        chunk_index = chunks_acked
        while True:
            data = f.read(CHUNK_SIZE)
            if not data:
                break
            acked = _server_receive_chunk(filename, chunk_index, data)
            if not acked:
                break
            chunk_index += 1
            manifest[progress_key] = chunk_index
            save_manifest(manifest)  # persist which chunks are acknowledged

    final_path = os.path.join(REMOTE_DIR, filename) # Reassemble the chunks into the final received file
    with open(final_path, "wb") as out:
        i = 0
        while os.path.exists(os.path.join(REMOTE_DIR, f"{filename}.part{i}")):
            part_path = os.path.join(REMOTE_DIR, f"{filename}.part{i}")
            with open(part_path, "rb") as part:
                out.write(part.read())
            os.remove(part_path)
            i += 1

    received_hash = hash_file(final_path) # Integrity check  does the reassembled file match the original hash?
    if received_hash != file_hash:
        return False  # do not mark as synced and then will be retried next run
    manifest[path] = {"hash": file_hash, "mtime": os.path.getmtime(path), "synced_at": time.time(),}
    manifest.pop(progress_key, None)
    save_manifest(manifest)
    return True

def sync_directory(watch_dir):
    manifest = load_manifest()
    changed_files = find_changed_files(watch_dir, manifest)
    results = []
    for path, file_hash in changed_files:
        success = send_file(path, file_hash, manifest)
        results.append((path, success))
    return results
