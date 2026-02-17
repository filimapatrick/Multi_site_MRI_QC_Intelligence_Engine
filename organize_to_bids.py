import os
import shutil
import gzip
from pathlib import Path
import json

def organize_dataset(root_dir):
    """
    Reorganizes a flat directory of T1w files into BIDS format.
    Assumes files are like: my_bids_dataset/anat/sub-01_T1w.nii
    Moves to: my_bids_dataset/sub-01/anat/sub-01_T1w.nii.gz
    """
    root_path = Path(root_dir)
    anat_source = root_path / "anat"
    
    if not anat_source.exists():
        print(f"❌ Error: Could not find source directory: {anat_source}")
        return

    print(f"📂 Scanning {anat_source}...")
    
    # 1. Create dataset_description.json
    desc_file = root_path / "dataset_description.json"
    if not desc_file.exists():
        description = {
            "Name": "Reorganized Dataset",
            "BIDSVersion": "1.6.0",
            "Authors": ["Auto-Reorganized"]
        }
        with open(desc_file, "w") as f:
            json.dump(description, f, indent=4)
        print("✅ Created dataset_description.json")

    # 2. Process Files
    moved_count = 0
    
    # Look for .nii and .nii.gz files
    for file_path in list(anat_source.glob("*.nii")) + list(anat_source.glob("*.nii.gz")):
        filename = file_path.name
        
        # Simple subject extraction (assumes sub-XX_...)
        parts = filename.split('_')
        subject_id = None
        for part in parts:
            if part.startswith('sub-'):
                subject_id = part
                break
        
        if not subject_id:
            print(f"⚠️ Skipping {filename}: Could not find 'sub-' identifier.")
            continue
            
        # Target Directory
        target_dir = root_path / subject_id / "anat"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Target Filename (ensure .nii.gz)
        if filename.endswith(".nii"):
            target_filename = filename + ".gz"
            target_path = target_dir / target_filename
            
            print(f"📦 Gzipping and moving {filename} -> {target_path}")
            with open(file_path, 'rb') as f_in:
                with gzip.open(target_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            file_path.unlink() # Remove original after successful gzip
            
        else:
            target_path = target_dir / filename
            print(f"🚚 Moving {filename} -> {target_path}")
            shutil.move(str(file_path), str(target_path))
            
        moved_count += 1

    # Cleanup empty anat folder if empty
    if not any(anat_source.iterdir()):
        anat_source.rmdir()
        print("🗑️ Removed empty source directory.")

    print(f"\n✨ Done! Reorganized {moved_count} files into BIDS format.")

if __name__ == "__main__":
    organize_dataset("my_bids_dataset")
