"""A collection of methods for use in processing and reducing data for CYCLOPS-VIPA"""
import numpy as np
import os

def VIPA_subtraction(sweepFolder, preserve_noise = True):
    """
    VIPA_subtraction will run through an entire test folder and produce subtracted images and reverse subtracted image. Optional kwarg to remove noise
    
    :param sweepFolder: Directory of test
    :param preserve_noise: bool, subtract average background?
    """
    with os.scandir(sweepFolder) as LOCS:
        for LOC in LOCS:
            if LOC.is_dir():
                with os.scandir(f"{sweepFolder}\\{LOC.name}") as TEMPS:
                    for TEMP in TEMPS: #running down dirs
                        if TEMP.is_dir():
                            ONimage = np.fliplr(np.loadtxt(f"{sweepFolder}\\{LOC.name}\\{TEMP.name}\\imageON.csv", delimiter=",", dtype = np.double))
                            OFFimage = np.fliplr(np.loadtxt(f"{sweepFolder}\\{LOC.name}\\{TEMP.name}\\imageON.csv", delimiter=",", dtype = np.double))
                            fsys_topdown = f"{sweepFolder}\\{LOC.name}\\{TEMP.name}"
                            if preserve_noise == True:
                                SUBimage = ONimage-OFFimage
                                SUBimage_rev = OFFimage-ONimage
                                np.savetxt(f"{fsys_topdown}\\imageSUB.csv", SUBimage, delimiter=",")
                                np.savetxt(f"{fsys_topdown}\\imageSUB_rev.csv", SUBimage_rev, delimiter=",")
                            else:
                                SUBimage = ONimage-OFFimage
                                SUBimage_noisePatch = np.mean(SUBimage[0:20,:]) #taking noise pixels from top 20 stripe
                                SUBimage_rev = OFFimage-ONimage
                                SUBimage_rev_noisePatch = np.mean(SUBimage_rev[0:20,:])

                                SUBimage = SUBimage - SUBimage_noisePatch
                                SUBimage_rev = SUBimage_rev - SUBimage_rev_noisePatch  #basic subtract average noise

                                np.savetxt(f"{fsys_topdown}\\imageSUB.csv", SUBimage, delimiter=",")
                                np.savetxt(f"{fsys_topdown}\\imageSUB_rev.csv", SUBimage_rev, delimiter=",") #save image in same dir
    pass