import pandas as pd
import numpy as np
import glob
import re
import argparse


def read_log(path, runname):

    with open(path, 'r') as f:
        results = f.readlines()
        
    nobs_final = int(re.findall(r'\d+', results[10])[0])
    transform_effect = results[11].split(':')[1].replace(r' ', '')[:-1]
    
    estimates = eval(re.sub('Estimates:', '', results[13])[:-1])
    h2_dir = estimates['v1']
    h2_indir = estimates['v2']
    r = estimates['r']
    
    se = re.findall(r'\d+.\d+', 
                re.sub('Standard Errors:', '', results[14])[:-1]
                .strip()
                .strip('[')
                .strip(']'))
    h2_dir_se = float(se[0])
    h2_indir_se = float(se[1])
    r_se = float(se[2])
    
    
    solver_output = ''
    for output in results[15:24]:
        solver_output += output
        
    estimation_time_prejk = re.sub('Estimation time:', '', results[24][:-1]).strip().split(':')
    estimation_time_prejk = f"{estimation_time_prejk[0]} hours, {estimation_time_prejk[1]} minutes, {estimation_time_prejk[2]} seconds"
    
    # If jkse is done
    if len(results) == 29:
        jk_blocksizes = int(re.findall(r'\d+', results[25])[0])
        jk_ncores = int(re.findall(r'\d+', results[26])[0])
        
        jkse = re.findall(r'\d+.\d+', 
                re.sub('Standard Errors:', '', results[27])[:-1]
                .strip()
                .strip('[')
                .strip(']'))
        h2_dir_jkse = float(jkse[0])
        h2_indir_jkse = float(jkse[1])
        r_jkse = float(jkse[2])
        
        estimation_time_postjk = re.findall(r'\d+', results[28])
        estimation_time_postjk = f"{estimation_time_postjk[0]} hours, {estimation_time_postjk[1]} minutes, {estimation_time_postjk[2]} seconds"
    else:
        jk_blocksizes = ""
        jk_ncores = ""
    
        h2_dir_jkse = ""
        h2_indir_jkse = ""
        r_jkse = ""
        
        estimation_time_postjk = ""
        
    outdf = pd.DataFrame(
        {
            'run' : runname,

            'solver_output' : solver_output,

            'nobs_final' : nobs_final,
            'transform_effect' : transform_effect,

            'h2_dir' : h2_dir,
            'h2_indir' : h2_indir,
            'r' : r,

            'h2_dir_se' : h2_dir_se,
            'h2_indir_se' : h2_indir_se,
            'r_se' : r_se,

            'estimation_time_prejk' : estimation_time_prejk,

            'jk_blocksizes' : jk_blocksizes,
            'jk_ncores' : jk_ncores,
            'h2_dir_jkse' : h2_dir_jkse,
            'h2_indir_jkse' : h2_indir_jkse,
            'r_jkse' : r_jkse,

            'estimation_time_postjk' : estimation_time_postjk

        },

        index = [0]
    )
        
        return outdf
    
    
def read_all_files(files, runnames):

    dfout = pd.DataFrame(
        columns = ['solver_output', 'nobs_final', 'transform_effect',
                    'h2_dir', 'h2_indir', 'r',
                    'h2_dir_se', 'h2_indir_se',  'r_se',
                    'estimation_time_prejk', 'jk_blocksizes', 'jk_ncores',
                    'h2_dir_jkse',  'h2_indir_jkse', 'r_jkse', 'estimation_time_postjk']
    )
    paths = glob.glob(files)
    for path, name in zip(paths, runnames):
        df_path = read_log(path, name)
        dfout = dfout.append(df_path).reset_index()
        
    return dfout

    

if __name__ == '__main__':
    
    parser=argparse.ArgumentParser()
    parser.add_argument('filenames', type = str,
                       help = 'Input log file names. Format should be glob like')
    parser.add_argument('--outpath', type = str,
                       help = 'Full path of outputted csv file. Include .csv in name')
    parser.add_argument('--runnames', type = str,
                       help = '''Comma delimited list of run names. Eg: "1,2,3,4,5"
                       If nothing is provided or if length is not equal to
                       length of filenames, the path is the runname.
                       ''')
    
    args = parser.parse_args()
    
    runnames = [item.strip() for item in args.runnames.split(',')]
    if runnnames == len(glob.glob(filenames)):
        dfout = read_all_files(args.filenames,
                              args.runnames)
    else:
        dfout = read_all_files(args.filenames,
                              args.filenames)
    
    dfout.to_csv(args.outpath,
                index = False)
    