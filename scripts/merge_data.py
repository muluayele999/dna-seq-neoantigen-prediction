import sys
import os
import pandas as pd
import numpy as np


def merge(info, tumor, normal, outfile):
    rank_cols = [c for c in tumor.columns if "Rank" in c]
    affinity_cols = [c for c in tumor.columns if "nM" in c]
    mhc_cols = ["ID"] + ["Peptide"] + rank_cols + affinity_cols + ["NB"]
    tumor = tumor[mhc_cols]
    normal = normal[mhc_cols]
    for mhc in [tumor, normal]:
        mhc["Rank_min"] = mhc[rank_cols].min(axis=1)
        mhc["Aff_min"] = mhc[affinity_cols].min(axis=1)
        mhc["Top_rank_HLA"] = mhc[rank_cols].idxmin(axis=1)
        mhc["Top_affinity_HLA"] = mhc[affinity_cols].idxmin(axis=1)
        mhc["Top_rank_HLA"] = mhc["Top_rank_HLA"].str.replace("Rank_","")
        mhc["Top_affinity_HLA"] = mhc["Top_affinity_HLA"].str.replace("nM_","")
    info["ID"] = info["id"].astype(str).str[:-1]

    merged_mhc = tumor.merge(normal,how='left', on='ID')
    merged_mhc = merged_mhc.rename(columns={col: col.replace("_y","_normal") for col in merged_mhc.columns}).rename(columns={col: col.replace("_x","_tumor") for col in merged_mhc.columns})

    info = info.rename(columns={"gene_id":"Gene_ID","gene_name":"Gene_Symbol","strand":"Strand","positions":"Variant_Position","chrom":"Chromosome","somatic_aa_change":"Somatic_AminoAcid_Change"})

    merged_dataframe = merged_mhc.merge(info, how='left', on = 'ID')



    merged_dataframe["Peptide_tumor"]=merged_dataframe[["Peptide_tumor","Peptide_normal"]].apply(lambda x: diffEpitope(*x), axis=1)
    ## Are all possible variants in the peptide ("Cis") or not ("Trans")
    merged_dataframe["Variant_Orientation"] = "Cis"
    trans = merged_dataframe.nvariant_sites > merged_dataframe.nvar
    merged_dataframe.loc[trans, "Variant_Orientation"] = "Trans"

    ## check misssense/silent mutation status
    nonsilent = merged_dataframe.Peptide_tumor != merged_dataframe.Peptide_normal
    merged_dataframe = merged_dataframe[nonsilent]
    merged_dataframe = merged_dataframe.drop_duplicates(subset=["Gene_ID","offset","Peptide_tumor","Somatic_AminoAcid_Change"])

    data = merged_dataframe[["ID","Gene_ID","Gene_Symbol","Chromosome","offset","freq",
"Somatic_AminoAcid_Change","Peptide_tumor","NB_tumor","Rank_min_tumor","Aff_min_tumor",
"Top_rank_HLA_tumor","Top_affinity_HLA_tumor","Peptide_normal","NB_normal",
"Rank_min_normal","Aff_min_normal","Top_rank_HLA_normal","Top_affinity_HLA_normal"]]

    data.columns = ["ID","Gene_ID","Gene_Symbol","Chromosome","Position","Frequency",
"Somatic_AminoAcid_Change","Peptide_tumor","BindingHLAs_tumor","Rank_min_tumor","Affinity_min_tumor",
"Top_rank_HLA_tumor","Top_affinity_HLA_tumor","Peptide_normal","BindingHLAs_normal",
"Rank_min_normal","Aff_min_normal","Top_rank_HLA_normal","Top_affinity_HLA_normal"]

    data = data[data.BindingHLAs_tumor > 0]
    # data = data[(data.NB_normal.isna()) | (data.NB_normal == 0)]
    data = data[(data.BindingHLAs_normal == 0)]

    ### Delete Stop-Codon including peptides
    data = data[data.Peptide_tumor.str.count("x") == 0]
    data = data[data.Peptide_tumor.str.count("X") == 0]

    data.to_csv(outfile, index=False, sep = '\t')


## highlight the difference between mutated neopeptide and wildtype
def diffEpitope(e1,e2):
    if str(e2) == 'nan':
        return(e1)
    e1 = str(e1)
    e2 = str(e2)
    diff_pos = [i for i in range(len(e1)) if e1[i] != e2[i]]
    e_new = e1
    e2_new = e2
    for p in diff_pos:
        e_new = e_new[:p] + e_new[p].lower() + e_new[p+1:]
        e2_new = e2_new[:p] + e2_new[p].lower() + e2_new[p+1:]
    return(e_new)


def main():
    info = pd.read_csv(snakemake.input[0], sep = ',')
    tumor = pd.read_csv(snakemake.input[1], sep = '\t')
    normal = pd.read_csv(snakemake.input[2], sep = '\t')
    outfile = snakemake.output[0]
    merge(info, tumor, normal, outfile)

if __name__ == '__main__':
    sys.exit(main())
