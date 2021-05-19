import numpy as np
import h5py
import glob
import datetime
import matplotlib.pyplot as plt
import pandas as pd
import logging
import argparse

import sys
import os
import sib_ldsc_z as ld

def print_call(call):
    
    '''
    Gives the call given to python
    in a nice string
    '''
    
    message = ''
    for i in range(len(call)):
        if call[i][0] != "-":
            message += call[i]
            message += ' \\ \n'
        else:
            message += call[i] + " "
    
    return message[1:-1]


def read_hdf5(args):

    # == Reading in data == #
    print("Reading in Data")
    # reading in  data
    filenames = args.path2file
    files = glob.glob(filenames)

    file = files[0]
    print("Reading in file: ", file)
    hf = h5py.File(file, 'r')
    metadata = hf.get(args.bim)[()]
    chromosome = metadata[:, args.bim_chromosome]
    bp = metadata[:, args.bim_bp]
    if args.rsid_readfrombim is not None:
        snp = np.zeros(bp.shape[0])
    else:
        snp = metadata[:, args.bim_rsid]
    A1 = metadata[:, args.bim_a1]
    A2 = metadata[:, args.bim_a2]
    theta  = hf.get(args.estimate)[()]
    se  = hf.get(args.estimate_ses)[()]
    S = hf.get(args.estimate_covariance)[()]
    f = hf.get(args.freqs)[()]

    # normalizing S
    sigma2 = hf.get(args.sigma2)[()]
    tau = hf.get(args.tau)[()]
    phvar = sigma2+sigma2/tau
    
    hf.close()

    if len(files) > 1:
        for file in files[1:]:
            print("Reading in file: ", file)
            hf = h5py.File(file, 'r')
            metadata = hf.get(args.bim)[()]
            chromosome_file = metadata[:, args.bim_chromosome]
            bp_file = metadata[:, args.bim_bp]
            if args.rsid_readfrombim:
                snp_file = np.zeros(bp_file.shape[0])
            else:
                snp_file = metadata[:, args.bim_rsid]
            A1_file = metadata[:, args.bim_a1]
            A2_file = metadata[:, args.bim_a2]
            theta_file  = hf.get(args.estimate)[()]
            se_file  = hf.get(args.estimate_ses)[()]
            S_file = hf.get(args.estimate_covariance)[()]
            f_file = hf.get(args.freqs)[()]

            chromosome = np.append(chromosome, chromosome_file, axis = 0)
            snp = np.append(snp, snp_file, axis = 0)
            bp = np.append(bp, bp_file, axis = 0)
            A1 = np.append(A1, A1_file, axis = 0)
            A2 = np.append(A2, A2_file, axis = 0)
            theta = np.append(theta, theta_file, axis = 0)
            se = np.append(se, se_file, axis = 0)
            S = np.append(S, S_file, axis = 0)
            f = np.append(f, f_file, axis = 0)
            hf.close()

    # Constructing dataframe of data
    zdata = pd.DataFrame({'CHR' : chromosome.astype(float).astype(int),
                        'SNP' : snp.astype(str),
                        'BP' : bp.astype(float).astype(int),
                        "f" : f,
                        "A1" : A1.astype(str),
                        "A2" : A2.astype(str),
                        'theta' : theta.tolist(),
                        'se' : se.tolist(),
                        "S" : S.tolist()})
    

    if args.rsid_readfrombim is not None:

        rsid_parts = args.rsid_readfrombim.split(",")
        rsidfiles = rsid_parts[0]
        bppos = int(rsid_parts[1])
        rsidpos = int(rsid_parts[2])
        file_sep = str(rsid_parts[3])

        rsidfiles = glob.glob(rsidfiles)
        snps = pd.DataFrame(columns = ["BP", "rsid"])
        for file in rsidfiles:
            snp_i = ld.return_rsid(file, bppos, rsidpos, file_sep)
            snps = snps.append(snp_i, ignore_index = True)
        
        snps = snps.drop_duplicates(subset=['BP'])
        zdata = zdata.merge(snps, how = "left", on = "BP")
        zdata = zdata.rename(columns = {"SNP" : "SNP_old"})
        zdata = zdata.rename(columns = {"rsid" : "SNP"})

    return zdata

def filter_maf(df, maf):

    dfcopy = df.copy()
    dfcopy = dfcopy[dfcopy['f'] >= maf/100.0]
    dfcopy = dfcopy[dfcopy['f'] <= 1-(maf/100.0)]

    return dfcopy


def read_txt(args):
    
    indirect_effect = args.txt_effectin
    dfin = pd.read_csv(args.path2file, delim_whitespace = True)
    N = dfin.shape[0]
    
    theta = np.zeros((N, 2))
    theta[:, 0] = np.array(dfin["direct_Beta"].tolist())
    theta[:, 1] = np.array(dfin[f'{indirect_effect}_Beta'].tolist())   
    
    
    se = np.zeros((N, 2))
    se[:, 0] = np.array((dfin["direct_SE"]).tolist())
    se[:, 1] = np.array((dfin[f'{indirect_effect}_SE']).tolist()) 
    
    S = np.zeros((N, 2, 2))
    S[:, 0, 0] = np.array((dfin["direct_SE"]**2).tolist())
    S[:, 1, 1] = np.array((dfin[f'{indirect_effect}_SE']**2).tolist()) 
    
    cov = dfin["direct_SE"] * dfin[f'{indirect_effect}_SE'] * dfin[f'r_direct_{indirect_effect}']
    S[:, 0, 1] = np.array(cov.tolist()) 
    
    zdata = pd.DataFrame({'CHR' : dfin['chromosome'].astype(int),
                    'SNP' : dfin['SNP'].astype(str),
                    'BP' : dfin['pos'].astype(int),
                    "f" : dfin['freq'],
                    "A1" : dfin['A1'].astype(str),
                    "A2" : dfin['A2'].astype(str),
                    'theta' : theta.tolist(),
                    'se' : se.tolist(),
                    "S" : S.tolist()})
    
    if args.rsid_readfrombim is not None:

        rsid_parts = args.rsid_readfrombim.split(",")
        rsidfiles = rsid_parts[0]
        bppos = int(rsid_parts[1])
        rsidpos = int(rsid_parts[2])
        file_sep = str(rsid_parts[3])
        
        rsidfiles = glob.glob(rsidfiles)
        snps = pd.DataFrame(columns = ["BP", "rsid"])
        for file in rsidfiles:
            snp_i = ld.return_rsid(file, bppos, rsidpos, file_sep)
            snps = snps.append(snp_i, ignore_index = True)
        
        snps = snps.drop_duplicates(subset=['BP'])
        zdata = zdata.merge(snps, how = "left", on = "BP")
        zdata = zdata.rename(columns = {"SNP" : "SNP_old"})
        zdata = zdata.rename(columns = {"rsid" : "SNP"})

    
    return zdata

def read_file(args):

    # what kind of file is it
    reader = args.path2file.split(".")[-1]
    print(reader)

    if reader == "hdf5":
        zdata = read_hdf5(args)
    elif reader == "txt":
        zdata = read_txt(args)
    else:
        raise Exception("Input file extension should either be hdf5 or txt")


    return zdata
    

if __name__ == '__main__':
    # command line arguments
    parser=argparse.ArgumentParser()
    parser.add_argument('path2file', type=str, 
                        help='''Path to hdf5 file or txt with summary statistics. 
                                                Should include the file name.
                                                In case of multiple files include glob character.
                                                eg: /path/to/file/chr_*.hdf5''')
    parser.add_argument('-effectin', '--txt-effectin', type = str, default = 'avg_parental',
    help = '''
    If input is a txt file, determines what the name of the indirect effect columns
    are. For example can be avgparental or population. By default its avg_parental.
    ''')
    parser.add_argument('-ldsc', '--ldsc_scores', type = str, required = True, help = '''Directory of LDSC scores.''')
    parser.add_argument('-m', '--mfiles', type = str, help = '''Directory of M files scores. If left blank M will be
                                                                the number of observations''')
    parser.add_argument('-l', '--logfile', type=str, help = '''The log file where the results will be stored.
                                                        If left blank no log file will be saved.''')
    parser.add_argument('-e', '--effect_transform', type = str, help ='''
                                                            How to convert the 3 dimensional data
                                                            into 2 dimensions. Options are direct_plus_population,
                                                            direct_plus_averageparental, full and population. 
                                                            Default is direct_plus_population.''')
    parser.add_argument('--rbound', dest = "rbounds", action='store_true')
    parser.add_argument('--no-rbound', dest = "rbounds", action = 'store_false')
    parser.set_defaults(rbounds=True)
    
    parser.add_argument('--jkse', dest = "jkse", action = 'store_true', help = '''
    Specifies if one wants to estimate block Jack Knife Standard errors
    ''')
    parser.set_defaults(jkse=False)
    parser.add_argument('--jkse_nblocks', type = int,
                    help = "Number of blocks for block jack knife SE estimation.")
    parser.add_argument('--jkse_blocksize', type = int, help = "Block Size for Block Jackknife Standard Errors.")
    parser.add_argument('--jkse_cores', type = int, help = "Number of cores to use for block Jack Knife standard errors.")
    parser.set_defaults(jkse_cores = 2)
    # parser.add_argument('--rbound-jkse', dest = "rbounds_jkse", action='store_true')
    # parser.add_argument('--no-rbound-jkse', dest = "rbounds_jkse", action = 'store_false')

    parser.add_argument('-maf', '--maf-thresh', dest = "maf", type = float, help = """The threshold of minor allele frequency. All SNPs below this threshold
                                                                        are dropped. Default is 5 percent. Set number as the percentage i.e. 5 instead of 0.05""")
    parser.set_defaults(maf = 5.0)
    parser.add_argument('--print-delete-values', dest = 'store_delvals', action = 'store_true',
    help = 'Option to save jack knife delete values. Saves to same location as log file.')

    # names of variable names
    parser.add_argument('-bim', default = "bim", type = str, help = "Name of bim column")
    parser.add_argument('-bim_chromosome', default = 0, type = int, help = "Column index of Chromosome in BIM variable")
    parser.add_argument('-bim_rsid', default = 1, type = int, help = "Column index of SNPID (RSID) in BIM variable")

    parser.add_argument('--rsid_readfrombim', type = str, 
                        help = '''Needs to be a comma seperated string of filename, BP-position, SNP-position, seperator.
                        If provided the variable bim_snp wont be used instead rsid's will be read
                        from the provided file set.''')
    parser.add_argument('-bim_bp', default = 3, type = int, help = "Column index of BP in BIM variable")
    parser.add_argument('-bim_a1', default = 4, type = int, help = "Column index of Chromosome in A1 variable")
    parser.add_argument('-bim_a2', default = 5, type = int, help = "Column index of Chromosome in A2 variable")

    parser.add_argument('-estimate', default = "estimate", type = str, help = "Name of estimate column")
    parser.add_argument('-estimate_ses', default = "estimate_ses", type = str, help = "Name of estimate_ses column")
    parser.add_argument('-N', default = "N_L", type = str, help = "Name of N column")
    parser.add_argument('-estimate_covariance', default = "estimate_covariance", type = str, help = "Name of estimate_covariance column")
    parser.add_argument('-freqs', default = "freqs", type = str, help = "Name of freqs column")

    parser.add_argument('-sigma2', default = "sigma2", type = str, help = "Name of sigma2 column")
    parser.add_argument('-tau', default = "tau", type = str, help = "Name of tau column")

    args=parser.parse_args()
    
    
    if args.jkse_blocksize is not None and args.jkse == False:
        print('''Option for Block Jack Knife block size was passed but wasn't told to actually estimate
                Block Jackknife Standard Errors. Script will run but will not estimate Block Jack Knife Standard
                Errors.''')
    
    
    if args.jkse_cores is not None and args.jkse == False:
        print('''Option for Block Jack Knife cores was passed but wasn't told to actually estimate
                Block Jackknife Standard Errors. Script will run but will not estimate Block Jack Knife Standard
                Errors.''')
    
    if args.logfile is not None:
        logging.basicConfig(filename= args.logfile, 
                                 level = logging.INFO,
                                 format = "%(message)s",
                                 filemode = "w")
        
    args_call = print_call(sys.argv)
    print(args_call)
    if args.logfile is not None:
        logging.info(f"Call: \n {args_call}")

    
    startTime = datetime.datetime.now()
    
    print(f"===============================")
    print(f"Start time:  {startTime}")
    
    if args.logfile is not None:
        logging.info(f"Start time:  {startTime}")
    
    
    zdata = read_file(args)

    zdata_n_message = f"Number of Observations before merging LD-Scores, before removing low MAF SNPs: {zdata.shape[0]}"
    
    print(zdata_n_message)
    if args.logfile is not None:
        logging.info(zdata_n_message)
    
    # dropping obs based on MAF
    zdata = filter_maf(zdata, args.maf)
    
    zdata_n_message = f"Number of Observations before merging LD-Scores, after removing low MAF SNPs: {zdata.shape[0]}"
    
    print(zdata_n_message)
    if args.logfile is not None:
        logging.info(zdata_n_message)


    # == Reading in LD Scores == #
    ldscore_path = args.ldsc_scores
    ldcolnames = ["CHR", "SNP", "BP", "L2"]
    ldscores= ld.read_ldscores(ldscore_path, ldcolnames)
    ldscores['BP'] = ldscores['BP'].astype('int')

    # dropping NAs
    main_df = zdata.merge(ldscores, how = "inner", on = ["SNP"], suffixes = ["", "_ld"])

    if main_df.shape[0] > 0:
        bp_align = np.all(main_df.BP == main_df.BP_ld)
        print(f"All BPs align: {bp_align}")

        if not bp_align:
            print(f"WARNING: {(main_df.BP != main_df.BP_ld).sum()} BPs don't match between data and reference LD sample.")
        main_df = main_df.drop('BP_ld', axis = 1)
        main_df = main_df.dropna()
    elif main_df.shape[0] == 0:
        print("No matches while matching LD-score data with main dataset using RSID.")
        print("Trying to match with BP.")
        main_df = zdata.merge(ldscores, how = "inner", on = ["BP"], suffixes = ["", "_ld"])
        main_df = main_df.drop('SNP_y', axis = 1)
        main_df = main_df.rename(columns = {'SNP_x' : 'SNP'})
        main_df = main_df.dropna()

    maindata_n_message = f"Number of Observations after merging LD-Scores and dropping NAs: {main_df.shape[0]}"
    main_df = main_df.sort_values(by=['CHR_ld', 'BP'])

    print(maindata_n_message)
    if args.logfile is not None:
        logging.info(maindata_n_message)

    # transforming inputs

    S = np.array(list(main_df.S)) 
    theta = np.array(list(main_df.theta))
    f = np.array(list(main_df["f"]))
    l = np.array(list(main_df["L2"]))
    u = np.array(list(main_df["L2"]))
    
    if args.mfiles is not None:
        Mfiles = args.mfiles
        Mcolnames = ["M", "CHR"]
        nloci = ld.read_mfiles(Mfiles, Mcolnames)
        M = nloci['M'].sum()
    else:
        M = len(S)
    
    if args.effect_transform is not None:
        effect_estimated = args.effect_transform
    else:
        effect_estimated = "direct_plus_population"
    
    effect_message = f"Transforming effects into: {effect_estimated}"

    print(effect_message)
    if args.logfile is not None:
        logging.info(effect_message)

    S, theta = ld.transform_estimates(effect_estimated, S, theta)

    # making z value
    zval = ld.theta2z(theta, S, M = M)

    # == Initializing model == #
    model = ld.sibreg(S = S, 
                    z = zval, 
                    l = l,
                    f = f,
                    u = u,
                    M = M) 

    output_matrix, result = model.solve(rbounds = args.rbounds)
    
    estimates = {'v1' : output_matrix['v1'],
                'v2' : output_matrix['v2'],
                'r' : output_matrix['r']}
    
    std_errors = np.diag(output_matrix['std_err_mat'])
    
    estimationTime = (datetime.datetime.now() - startTime)
    
    print("----------------------------------")
    print(f"Estimates: {estimates}")
    print(f"Standard Errors: {std_errors}")
    print(f"Maximizer Output: {result}")
    print(f"Estimation time: {estimationTime}")
    
    if args.logfile is not None:
        logging.info("----------------------------------")
        logging.info(f"Estimates: {estimates}")
        logging.info(f"Standard Errors: {std_errors}")
        logging.info(f"Maximizer Output: {result}")
        logging.info(f"Estimation time: {estimationTime}")
        
    if args.jkse:
        
        if args.jkse_nblocks is not None:
            nblocks_blocksize = np.ceil(zval.shape[0]/args.jkse_nblocks)
            blocksize = int(nblocks_blocksize)
        elif args.jkse_blocksize is not None and args.jkse_nblocks is None:
            # need nblocks to always override blocksize option
            blocksize = int(args.jkse_blocksize)
        else:
            nblocks = 200
            nblocks_blocksize = np.ceil(zval.shape[0]/nblocks)
            blocksize = int(nblocks_blocksize)

            

        print(f"Jack Knife Block Sizes = {blocksize}")
        print(f"Number of cores being used for Jack Knife: {args.jkse_cores}")
        print("Estimating Block Jackknife Standard Errors...")

        # rbounds
        rbounds_jkse = args.rbounds #if args.rbounds_jkse is None else args.rbounds_jkse
        
        initguess = {'v1' : phvar/2, 'v2' : phvar/2, 'r' : 0.0} #output_matrix
        jkse, delvals = ld.jkse(model, initguess, blocksize = blocksize, num_procs=args.jkse_cores,
                        rbounds = rbounds_jkse)

        if args.store_delvals:
            if args.logfile is not None:
                np.savetxt(f"{args.logfile}.txt", delvals)

        print(f"Block Jack Knife Standard Errors: {jkse}")
        
        estimationTime_jkse = (datetime.datetime.now() - startTime)
        
        print(f"Estimation time with Block Jack Knife Standard Error Estimation: {estimationTime_jkse}")
        

        if args.logfile is not None:
            logging.info(f"Jack Knife Block Sizes = {blocksize}")
            logging.info(f"Number of cores being used for Jack Knife: {args.jkse_cores}")
            logging.info(f"Block Jack Knife Standard Errors: {jkse}")
            logging.info(f"Estimation time with Block Jack Knife Standard Error Estimation: {estimationTime_jkse}")
            
            