# Scientific Background: MRI Quality Control

## Overview

Magnetic Resonance Imaging (MRI) quality control is essential for ensuring reliable and reproducible neuroimaging research. This document provides the scientific foundation for the quality metrics implemented in the MRI QC Intelligence Engine.

## Structural MRI Quality Metrics

### Signal-to-Noise Ratio (SNR)

**Definition**: The ratio of signal intensity in brain tissue to the standard deviation of noise in background regions.

**Formula**: 
```
SNR = μ_signal / σ_noise
```

**Clinical Significance**: 
- Higher SNR enables better tissue contrast discrimination
- SNR < 10 typically indicates poor image quality
- Affects subsequent processing steps (segmentation, registration)

**Implementation**: Signal measured from brain parenchyma, noise from image corners or background air regions.

### Contrast-to-Noise Ratio (CNR)

**Definition**: The difference in signal between two tissue types divided by noise.

**Formula**: 
```
CNR = |μ_tissue1 - μ_tissue2| / σ_noise
```

**Clinical Significance**:
- Critical for tissue segmentation accuracy
- GM/WM CNR < 5 may compromise morphometric analysis
- Scanner-dependent parameter requiring harmonization

### Intensity Non-Uniformity (INU)

**Definition**: Spatial variation in signal intensity across the image due to B1 field inhomogeneities.

**Formula**: 
```
INU = σ_brain / μ_brain
```

**Clinical Significance**:
- INU > 0.2 can bias volumetric measurements
- Requires N4 bias field correction in preprocessing
- More problematic at higher field strengths (3T, 7T)

## Functional MRI Quality Metrics

### Temporal Signal-to-Noise Ratio (tSNR)

**Definition**: Ratio of mean signal to temporal standard deviation across the time series.

**Formula**: 
```
tSNR = μ_temporal / σ_temporal
```

**Clinical Significance**:
- Fundamental metric for fMRI statistical power
- tSNR < 50 may limit activation detection
- Inversely related to thermal and physiological noise

### Framewise Displacement (FD)

**Definition**: Scalar measure of head motion between consecutive volumes.

**Formula**: 
```
FD[i] = |Δx[i]| + |Δy[i]| + |Δz[i]| + r|Δα[i]| + r|Δβ[i]| + r|Δγ[i]|
```
where r = 50mm (approximate brain radius)

**Clinical Significance**:
- Primary motion metric in fMRI analysis
- FD > 0.5mm threshold for motion censoring
- Correlates with motion-induced signal artifacts

**Reference**: Power et al., NeuroImage 2012

### DVARS

**Definition**: Temporal derivative of RMS variance over voxels.

**Formula**: 
```
DVARS[i] = √(〈[x[i] - x[i-1]]²〉)
```

**Clinical Significance**:
- Detects sudden signal changes from motion or scanner artifacts
- Complements FD for comprehensive motion assessment
- Used for automated outlier detection

**Reference**: Smyser et al., NeuroImage 2010

## Diffusion MRI Quality Metrics

### Signal Dropout Detection

**Definition**: Identification of slices with abnormally low signal due to cardiac pulsation, motion, or eddy currents.

**Method**: Compare slice-wise signal intensity to adjacent slices within each volume.

**Clinical Significance**:
- Critical for DTI/DKI parameter estimation
- Can bias tractography results
- Requires outlier replacement or exclusion

### B-value Consistency

**Definition**: Validation of gradient strength calibration across acquisition.

**Metrics**:
- Expected vs. actual b-value distributions
- Shell-wise direction count validation
- Cross-shell SNR consistency

**Clinical Significance**:
- Incorrect b-values bias diffusion parameter estimation
- Essential for multi-site harmonization
- Affects model fitting accuracy (DTI, NODDI, etc.)

### Gradient Direction Coverage

**Definition**: Assessment of spherical sampling uniformity on the diffusion encoding sphere.

**Method**: Electrostatic energy minimization assessment:
```
E = Σᵢⱼ 1/||gᵢ - gⱼ||
```

**Clinical Significance**:
- Poor coverage introduces directional bias
- Affects tensor estimation conditioning
- Critical for spherical deconvolution methods

**Reference**: Jones et al., MRM 1999

## Multi-Site Harmonization

### Scanner Effects

**Sources of Variation**:
- Vendor differences (Siemens, GE, Philips)
- Field strength (1.5T vs 3T)
- Gradient performance
- RF coil characteristics
- Software versions

### Statistical Harmonization

**Z-score Normalization**:
```
z = (x - μ_site) / σ_site
```

**ComBat Harmonization**:
- Empirical Bayes method for batch effect removal
- Preserves biological variation while removing technical variation
- Implemented for multi-site DTI studies

**Reference**: Fortin et al., NeuroImage 2017

## Outlier Detection Methods

### Statistical Approaches

**Modified Z-score** (Robust):
```
M = 0.6745 × (x - median) / MAD
```
where MAD = median absolute deviation

**Grubbs' Test**:
Detects single outliers in univariate distributions

### Machine Learning Approaches

**Isolation Forest**:
- Unsupervised anomaly detection
- Effective for high-dimensional data
- Contamination parameter controls sensitivity

**One-Class SVM**:
- Support vector approach to novelty detection
- Kernel methods for non-linear decision boundaries

**Reference**: Liu et al., IEEE ICDM 2008

## Quality Score Computation

### Weighted Composite Scoring

**Formula**:
```
QC_score = Σᵢ wᵢ × normalize(metric_i)
```

where:
- wᵢ = importance weight for metric i
- normalize() maps to 0-100 scale
- Weights sum to 1.0 per modality

### Normalization Strategy

**Robust Z-score** (preferred):
```
score = 50 ± z_robust × 15
```

**Percentile-based**:
```
score = 100 × percentile_rank(metric)
```

### Clinical Thresholds

| Score Range | Rating | Action |
|-------------|--------|---------|
| 75-100 | Pass | Proceed with analysis |
| 50-74 | Warning | Review manually |
| 0-49 | Fail | Exclude or reacquire |

## Validation Studies

### Test-Retest Reliability
- Intraclass correlation coefficient (ICC)
- Coefficient of variation (CV)
- Bland-Altman analysis

### Expert Agreement
- Cohen's kappa for categorical ratings
- Pearson correlation for continuous scores
- Sensitivity/specificity for outlier detection

### Clinical Outcomes
- Effect size preservation after QC
- False discovery rate control
- Statistical power analysis

## References

1. Mortamet B, et al. Automatic quality assessment in structural brain magnetic resonance imaging. Magn Reson Med. 2009;62(2):365-72.

2. Power JD, et al. Spurious but systematic correlations in functional connectivity MRI networks arise from subject motion. NeuroImage. 2012;59(3):2142-54.

3. Bastiani M, et al. Automated quality control for within and between studies diffusion MRI data using a non-parametric framework for movement and distortion correction. NeuroImage. 2019;184:801-12.

4. Esteban O, et al. MRIQC: Advancing the automatic prediction of image quality in MRI from unseen sites. PLoS One. 2017;12(9):e0184661.

5. Alfaro-Almagro F, et al. Image processing and Quality Control for the first 10,000 brain imaging datasets from UK Biobank. NeuroImage. 2018;166:400-24.

6. Fortin JP, et al. Harmonization of multi-site diffusion tensor imaging data. NeuroImage. 2017;161:149-70.

7. Karayumak SC, et al. Learning-based screening of endogenous lesions in multi-site structural MRI. NeuroImage. 2019;190:1-14.