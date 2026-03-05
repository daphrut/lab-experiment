# Load data
load("/Users/drutna/Library/CloudStorage/OneDrive-UniversitätZürichUZH/UZH Carbon Neutrality/4_Data/2_CleanedEnergyConsumption/UZH_lab_machine_data.RData")

################################################################################
# MeF 
################################################################################

# Tabulate the Typ Gerat variable in the MeF dataset
table(MeF$`Typ Gerät`)

# Try to find all -80 freezers
MeF$`Typ Gerät` <- tolower(MeF$`Typ Gerät`)

pattern1 <- "(-80.*(tief|freez|gefrierschrank|ult))|((tief|freez|gefrierschrank|ult).* -?80)"
pattern2 <- "-80"
pattern3 <- "minus 80"
pattern4 <- "deepfreezer"

matches <- grepl(pattern1, MeF$`Typ Gerät`) | grepl(pattern2, MeF$`Typ Gerät`) | grepl(pattern3, MeF$`Typ Gerät`) | grepl(pattern4, MeF$`Typ Gerät`)

MeF_ult <- subset(MeF, matches)

# Count number of lab groups with at least 1 ULT in the MeF dataset
no_ult_groups_mef <- length(unique(MeF_ult$`Geräteverantwortlicher Institut`))
print(no_ult_groups_mef)

################################################################################
# MNF 
################################################################################

# Tabulate the Typ Gerat variable in the MNF dataset
table(MNF$`Typ Gerät`)

# Try to find all -80 freezers
MNF$`Typ Gerät` <- tolower(MNF$`Typ Gerät`)

matches <- grepl(pattern1, MNF$`Typ Gerät`) | grepl(pattern2, MNF$`Typ Gerät`) | grepl(pattern3, MNF$`Typ Gerät`) | grepl(pattern4, MNF$`Typ Gerät`)

MNF_ult <- subset(MNF, matches)

# Count number of lab groups with at least 1 ULT in the MeF dataset
no_ult_groups_mnf <- length(unique(MNF_ult$`Geräteverantwortlicher / Arbeitsgruppenleiter`))
print(no_ult_groups_mnf)

