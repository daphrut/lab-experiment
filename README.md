# lab-experiment

# Lab Sustainability RCT

This repository contains all code for a randomized controlled trial (RCT) evaluating a laboratory sustainability intervention. 

The repository covers the full research pipeline: power calculations, randomization and treatment assignment, creation of intervention materials and endline survey files, data cleaning, and analysis.

> **Note:** Data files are not stored in this repository.

---

## Repository Structure

```
├── 1_Cleaning/         # Cleaning of raw survey and administrative electricity data
├── 2_Preparation/      # Randomization, treatment assignment, intervention materials,
│                       # and endline survey file creation
├── 3_Analysis/         # Power calculations, exploratory analysis, descriptives,
│                       # regressions, tables, and figures
├── z_old/              # Deprecated scripts (not maintained)
├── .gitignore
├── LICENSE
└── README.md
```

Scripts within each folder are numbered sequentially (e.g. `1_1_`, `1_2_`).

---

## Setup

### Environment

This project uses a conda environment called `labrct`. To recreate it:

```bash
# Coming soon — environment.yml will be added
conda activate labrct
```

**Python version:** 3.11.5

### Dependencies

A `environment.yml` will be added.

---

## Branches

- `main` — stable, merged code
- `cleaning` — data cleaning (merged into main)
- `nhr_cleaning` - data cleaning (merged into main)
- `analysis` — active analysis work

---

## Configuration

Copy `config_template.py` to `config.py` and fill in your local paths. 
`config.py` is not tracked in this repository.