import os
import numpy as np
import nibabel as nib
from pathlib import Path

def create_flat_dataset(root_dir):
    """Creates a flat dataset for testing auto-fix."""
    root_dir = Path(root_dir)
    anat_dir = root_dir / "anat"
    anat_dir.mkdir(parents=True, exist_ok=True)
    
    subjects = ["sub-01", "sub-02"]
    
    for sub in subjects:
        # Create Dummy T1w (flat)
        data = np.random.rand(64, 64, 64)
        img = nib.Nifti1Image(data, np.eye(4))
        
        # Save as .nii to test gzip conversion too
        nib.save(img, anat_dir / f"{sub}_T1w.nii")
        
    print(f"✅ Flat dataset created at: {root_dir}")

if __name__ == "__main__":
    create_flat_dataset("./test_flat_data")
