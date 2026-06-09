from pathlib import Path
import os

# ---------------------------
# Project paths configuration
# ---------------------------

# Personal OneDrive root (your own machine)
ONEDRIVE_ROOT = Path("/path/to/your/OneDrive/root")

# Personal econ server root (your own machine)
SERVER_ROOT = Path("/path/to/your/server/root")

# Personal switchdrive root (your own machine)
SWITCHDRIVE_ROOT = Path("/path/to/your/switchdrive/root")

# Personal overleaf root (your own machine)
OVERLEAF_ROOT = Path("/path/to/your/overleaf/root")

# Data folder
DATA_ROOT = SERVER_ROOT / "data"

# Backup data folder
BACKUP_ROOT = DATA_ROOT / "11_Backup"

# Data subfolders
LABS_LIST = DATA_ROOT / "9_Lab_Name_Location"
WAVE1_LABS_LIST = LABS_LIST / "1_MeFMNF"
WAVE2_LABS_LIST = LABS_LIST / "2_VetsuisseUSZ"
COMBINED_WAVES_LABS_LIST = LABS_LIST / "3_Combined"
DATA_TO_MERGE = DATA_ROOT / "10_Data_To_Merge"
ENUMERATORS = DATA_TO_MERGE / "1_Enumerators"
WAVE1_ENUMERATORS = ENUMERATORS / "1_MeFMNF"
WAVE2_ENUMERATORS = ENUMERATORS / "2_VetsuisseUSZ"
COMBINED_WAVES_ENUMERATORS = ENUMERATORS / "3_Combined"
SURVEY_DICTIONARIES = DATA_TO_MERGE / "2_Survey_Dictionaries"
DATA_DICTIONARIES = DATA_TO_MERGE / "3_Data_Dictionaries"
CLEANING_WORKBOOKS = DATA_TO_MERGE / "4_Cleaning_Workbooks"
SPARK_DATA = DATA_TO_MERGE / "5_SPARK_Calculator_Data"

# BL data folders
BL_DATA_ROOT = DATA_ROOT / "12_BL_Data"
BL_RAW_SAMPLE = BL_DATA_ROOT / "1_Sample"
BL_RAW_SURVEY = BL_DATA_ROOT / "2_Raw_Survey"
BL_RAW_CHECKLIST = BL_DATA_ROOT / "3_Raw_Checklist"

# BL backup data folders
BL_DATA_BACKUP = BACKUP_ROOT / "12_BL_Data"
BL_RAW_SAMPLE_BACKUP = BL_DATA_BACKUP / "1_Sample"
BL_RAW_SURVEY_BACKUP = BL_DATA_BACKUP / "2_Raw_Survey"
BL_RAW_CHECKLIST_BACKUP = BL_DATA_BACKUP / "3_Raw_Checklist"

# Calculators folder
CALCULATORS_ROOT = DATA_ROOT / "13_Calculators"
CALCULATORS_WITH_TIPS = CALCULATORS_ROOT / "8_Final_Calculators"

# EL survey folder (empty)
EL_EMPTY_ROOT = DATA_ROOT / "14_EL_Empty"

# EL data folders
EL_DATA_ROOT = DATA_ROOT / "15_EL_Data"
EL_RAW_SAMPLE = EL_DATA_ROOT / "1_Sample"
EL_RAW_SURVEY = EL_DATA_ROOT / "2_Raw_Survey"

# EL backup data folders
EL_DATA_BACKUP = BACKUP_ROOT / "15_EL_Data"
EL_RAW_SAMPLE_BACKUP = EL_DATA_BACKUP / "1_Sample"
EL_RAW_SURVEY_BACKUP = EL_DATA_BACKUP / "2_Raw_Survey"

# Processed data folder
PROCESSED_DATA = DATA_ROOT / "16_Processed_Data"

# Clean data folder
CLEAN_DATA = DATA_ROOT / "17_Clean_Data"

# Sensitive data folder
SENSITIVE_DATA = DATA_ROOT / "18_Sensitive_Data"

# Code folder (current folder)
CODE_ROOT = Path(__file__).resolve().parent

# Output folder
OUTPUT = OVERLEAF_ROOT / "2_Output"

# Set secret seed (for creating IDs)
SEED = ###

# FC confidential data
ELEC_PER_M3 = ###
GAS_PER_M3  = ###

