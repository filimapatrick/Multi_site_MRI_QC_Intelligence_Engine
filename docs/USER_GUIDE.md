# 🏥 User Guide: Adding Your Data

## 1. Prepare Your Data (BIDS Format)

The QC Engine requires your data to be in the **BIDS (Brain Imaging Data Structure)** format.

### Required Structure
Your folder should look like this:

```
my_bids_dataset/
├── dataset_description.json
├── participants.tsv
├── sub-01/
│   ├── anat/
│   │   └── sub-01_T1w.nii.gz          <-- Must end in _T1w.nii.gz
│   ├── func/
│   │   └── sub-01_task-rest_bold.nii.gz <-- Must end in _bold.nii.gz
│   └── dwi/
│       ├── sub-01_dwi.nii.gz          <-- Must end in _dwi.nii.gz
│       ├── sub-01_dwi.bval
│       └── sub-01_dwi.bvec
└── sub-02/
    └── ...
```

### Key Requirements
*   **Subject Folders:** Must start with `sub-`.
*   **Modality Files:**
    *   **T1w:** `*_T1w.nii.gz`
    *   **fMRI:** `*_bold.nii.gz`
    *   **DWI:** `*_dwi.nii.gz` (plus `.bval` and `.bvec` files)

## 2. Run the QC Engine

Once your data is ready, run the following command in your terminal:

```bash
# Activate the environment (if not already active)
source .venv/bin/activate

# Run QC (replace path with your actual data folder)
qc_engine --bids-dir /path/to/your/my_bids_dataset --output-dir ./qc_reports/my_analysis
```

### Options
*   `--modality T1w`: Only run T1w analysis (faster).
*   `--modality T1w,bold`: Run specific modalities.
*   `--detect-outliers`: Enable outlier detection (requires >5 subjects for meaningful results).
*   `--multi-site`: Enable site harmonization features.
