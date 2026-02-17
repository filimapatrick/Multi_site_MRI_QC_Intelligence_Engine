import os
import numpy as np
import nibabel as nib
import pandas as pd
from pathlib import Path

def create_dummy_bids_dataset(root_dir):
    """Creates a dummy BIDS dataset for testing."""
    root_dir = Path(root_dir)
    root_dir.mkdir(parents=True, exist_ok=True)
    
    # Dataset Description
    description = {
        "Name": "Dummy BIDS Dataset",
        "BIDSVersion": "1.6.0",
        "Authors": ["Automated Generator"]
    }
    import json
    with open(root_dir / "dataset_description.json", "w") as f:
        json.dump(description, f, indent=4)
        
    # Participants
    subjects = ["sub-01", "sub-02"]
    participants_df = pd.DataFrame({
        "participant_id": subjects,
        "age": [25, 30],
        "sex": ["M", "F"],
        "site": ["SiteA", "SiteB"]
    })
    participants_df.to_csv(root_dir / "participants.tsv", sep="\t", index=False)
    
    for sub in subjects:
        sub_dir = root_dir / sub
        anat_dir = sub_dir / "anat"
        func_dir = sub_dir / "func"
        dwi_dir = sub_dir / "dwi"
        
        anat_dir.mkdir(parents=True, exist_ok=True)
        func_dir.mkdir(parents=True, exist_ok=True)
        dwi_dir.mkdir(parents=True, exist_ok=True)
        
        # Create Dummy T1w
        # 64x64x64 image
        data = np.random.rand(64, 64, 64)
        img = nib.Nifti1Image(data, np.eye(4))
        nib.save(img, anat_dir / f"{sub}_T1w.nii.gz")
        
        # Create Dummy JSON for T1w
        with open(anat_dir / f"{sub}_T1w.json", "w") as f:
            json.dump({"RepetitionTime": 2.0, "EchoTime": 0.03}, f)

        # Create Dummy BOLD
        # 64x64x30x10 (10 timepoints)
        func_data = np.random.rand(64, 64, 30, 10)
        func_img = nib.Nifti1Image(func_data, np.eye(4))
        nib.save(func_img, func_dir / f"{sub}_task-rest_bold.nii.gz")
        
        with open(func_dir / f"{sub}_task-rest_bold.json", "w") as f:
            json.dump({"RepetitionTime": 2.0, "TaskName": "rest"}, f)

        # Create Dummy DWI
        dwi_data = np.random.rand(64, 64, 30, 10)
        dwi_img = nib.Nifti1Image(dwi_data, np.eye(4))
        nib.save(dwi_img, dwi_dir / f"{sub}_dwi.nii.gz")
        
        with open(dwi_dir / f"{sub}_dwi.json", "w") as f:
             json.dump({"RepetitionTime": 2.0}, f)
             
        # Create dummy bval and bvec
        np.savetxt(dwi_dir / f"{sub}_dwi.bval", np.random.randint(0, 3000, 10).reshape(1, -1), fmt='%d')
        np.savetxt(dwi_dir / f"{sub}_dwi.bvec", np.random.rand(3, 10), fmt='%.6f')

    print(f"✅ Dummy BIDS dataset created at: {root_dir}")

if __name__ == "__main__":
    create_dummy_bids_dataset("./dummy_bids_dataset")
