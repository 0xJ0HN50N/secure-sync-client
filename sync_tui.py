import os
import sync_logic

def print_menu():
    print("\n=== Minimal Sync Client ===")
    print("1. Sync a directory")
    print("2. View manifest (synced files)")
    print("3. Exit")

def sync_directory_flow():
    watch_dir = input("Directory to sync: ").strip()
    if not watch_dir or not os.path.isdir(watch_dir):
        print("Not a valid directory.")
        return

    print(f"Scanning '{watch_dir}' for changes...")
    results = sync_logic.sync_directory(watch_dir)
    if not results:
        print("Nothing to sync - no new or modified files found.")
        return
    for path, success in results:
        status = "OK" if success else "FAILED (integrity check)"
        print(f"  [{status}] {path}")

def view_manifest():
    manifest = sync_logic.load_manifest()
    if not manifest:
        print("No files have been synced yet.")
        return

    print("\nSynced files:")
    for path, info in manifest.items():
        if path.endswith(":progress"):
            continue
        print(f"  {path}  (hash: {info['hash'][:10]}...)")

def main():
    while True:
        print_menu()
        choice = input("Choose an option: ").strip()
        if choice == "1":
            sync_directory_flow()
        elif choice == "2":
            view_manifest()
        elif choice == "3":
            print("Goodbye.")
            break
        else:
            print("Invalid option, try again.")
if __name__ == "__main__":
    main()
