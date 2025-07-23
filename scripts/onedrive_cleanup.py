import os
import shutil

# List of problematic folder/file names
PROBLEM_NAMES = ['.config', '~']

# Root directory to scan (your project root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def is_problematic(name):
    return name in PROBLEM_NAMES

def cleanup_problematic_files(root):
    removed = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Clean folders
        for dirname in list(dirnames):
            if is_problematic(dirname):
                full_path = os.path.join(dirpath, dirname)
                try:
                    shutil.rmtree(full_path)
                    removed.append(full_path)
                    print(f"Removed folder: {full_path}")
                except Exception as e:
                    print(f"Failed to remove folder {full_path}: {e}")
        # Clean files
        for filename in list(filenames):
            if is_problematic(filename):
                full_path = os.path.join(dirpath, filename)
                try:
                    os.remove(full_path)
                    removed.append(full_path)
                    print(f"Removed file: {full_path}")
                except Exception as e:
                    print(f"Failed to remove file {full_path}: {e}")
    return removed

if __name__ == "__main__":
    print(f"Scanning for problematic files/folders in {PROJECT_ROOT} ...")
    removed = cleanup_problematic_files(PROJECT_ROOT)
    print(f"Cleanup complete. {len(removed)} items removed.") 