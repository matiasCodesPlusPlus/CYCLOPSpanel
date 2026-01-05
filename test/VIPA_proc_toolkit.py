"""A collection of methods for use in processing and reducing data for CYCLOPS-VIPA"""
import numpy as np
import os
import matplotlib.pyplot as plt
import csv

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

                            with open(f"{sweepFolder}\\{LOC.name}\\{TEMP.name}\\imageON.csv") as file:
                                reader = csv.reader(file)
                                ONimage = list(reader)
                            with open(f"{sweepFolder}\\{LOC.name}\\{TEMP.name}\\imageOFF.csv") as file:
                                reader = csv.reader(file)
                                OFFimage = list(reader)

                            ONimage = np.array(ONimage, dtype = float)
                            OFFimage = np.array(OFFimage, dtype = float)
                            #ONimage = np.fliplr(np.loadtxt(f"{sweepFolder}\\{LOC.name}\\{TEMP.name}\\imageON.csv", delimiter=","))
                            #OFFimage = np.fliplr(np.loadtxt(f"{sweepFolder}\\{LOC.name}\\{TEMP.name}\\imageON.csv", delimiter=","))
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

def VIPA_polarity(image1, image2):
    """easy little polarity checksum"""
    sum1 = np.sum(image1)
    sum2 = np.sum(image2)

    if sum1>sum2:
        return image1
    else:
        return image2
    

def VIPA_temp_sidebysides(testFolder):
    TOTAL_TEMPS = []
    TOTAL_IMAGES = []
    IMAGE_LOCS = []
    with os.scandir(testFolder) as LOCS:
        for LOC in LOCS:
            IMAGE_LOC = float(str(LOC.name).split("_")[1])
            IMAGE_LOCS.append(IMAGE_LOC)
            TEMPS_AT_IMAGE = []
            IMAGES = []
            with os.scandir(f"{testFolder}\\{LOC.name}") as TEMPS:
                
                for TEMP in TEMPS:
                    TEMP_AT_IMAGE = float(str(TEMP.name).split("_")[1])
                    image = np.loadtxt(f"{testFolder}\\{LOC.name}\\{TEMP.name}\\imageSUB.csv", delimiter=",")
                    imagerev = np.loadtxt(f"{testFolder}\\{LOC.name}\\{TEMP.name}\\imageSUB_rev.csv", delimiter=",")

                    image = VIPA_polarity(image, imagerev)

                    TEMPS_AT_IMAGE.append(TEMP_AT_IMAGE)
                    IMAGES.append(image)
            
            TEMPS_AT_IMAGE = np.array(TEMPS_AT_IMAGE)
            IMAGES = np.array(IMAGES)
            sorted_indices = np.argsort(TEMPS_AT_IMAGE)
            TEMPS_AT_IMAGE = TEMPS_AT_IMAGE[sorted_indices]
            IMAGES = IMAGES[sorted_indices]

            TOTAL_TEMPS.append(TEMPS_AT_IMAGE)
            TOTAL_IMAGES.append(IMAGES)
    
    IMAGE_LOCS = np.array(IMAGE_LOCS)
    TOTAL_TEMPS = np.array(TOTAL_TEMPS)
    TOTAL_IMAGES = np.array(TOTAL_IMAGES)
    cmin = np.min(TOTAL_IMAGES)
    cmax = np.max(TOTAL_IMAGES)
    fig,ax = plt.subplots(3,3)
    
    for ind, image in np.ndenumerate(TOTAL_IMAGES[:,:,0,0]):
        
        i, j = ind
        ax[i,j].imshow(np.fliplr(TOTAL_IMAGES[i,j]), cmap = "jet", vmin = cmin, vmax = cmax)
        ax[i,j].set_title(f"LOC: {IMAGE_LOCS[i]} TEMP: {TOTAL_TEMPS[i,j]}")
    plt.show()    
    pass

def VIPA_show_ONOFF(imageFolder):
    imageON = np.loadtxt(f"{imageFolder}\\imageON.csv", delimiter=",")
    imageOFF = np.loadtxt(f"{imageFolder}\\imageON.csv", delimiter=",")
    cmin = np.min((imageON, imageOFF))
    cmax = np.max((imageON, imageOFF))
    fig, ax = plt.subplots(1,2)

    ax[0].imshow(imageON, vmin = cmin, vmax = cmax)
    ax[1].imshow(imageOFF, vmin = cmin, vmax = cmax)
    plt.show()
    pass


def VIPA_focus_test(filePath):
    IMAGES = []
    SCREW_POSITIONS = []
    with os.scandir(filePath) as dirs:
        for dir in dirs:
            screwPos = float(str(dir.name).split("_")[1])
            imageON = np.loadtxt(f"{filePath}\\{dir.name}\\SHORT_EXP_ON.csv", delimiter=",")
            imageOFF = np.loadtxt(f"{filePath}\\{dir.name}\\SHORT_EXP_OFF.csv", delimiter=",")
            if np.sum(imageON-imageOFF) > np.sum(imageOFF-imageON):
                imageSUB = imageON - imageOFF
            else:
                imageSUB = imageOFF-imageON
            SUBimage_noisePatch = np.mean(imageSUB[0:20,:])
            imageSUB = imageSUB - SUBimage_noisePatch
            IMAGES.append(imageSUB)
            SCREW_POSITIONS.append(screwPos)
    IMAGES = np.array(IMAGES)
    SCREW_POSITIONS = np.array(SCREW_POSITIONS)

    sorted_idx = np.argsort(SCREW_POSITIONS)
    IMAGES = IMAGES[sorted_idx]
    SCREW_POSITIONS = SCREW_POSITIONS[sorted_idx]

    cmin = np.min(IMAGES)
    cmax = np.max(IMAGES)

    fig, ax = plt.subplots(1,len(SCREW_POSITIONS))
    for i in enumerate(SCREW_POSITIONS):
        ax[i].imshow(IMAGES[i], cmap = "jet", vmin = cmin, vmax = cmax)
        ax[i].set_title(f"screw position: {SCREW_POSITIONS[i]}")





if __name__ == "__main__":
    sweepFolder = "D:\\VIPA_TEST_DATA\\SWEEP_2026_01_05_08_49_25"
    #LOCFolder = "D:\\VIPA_TEST_DATA\\SWEEP_2026_01_05_08_49_25\\IMG_49.75"
    #imageFolder = "D:\\VIPA_TEST_DATA\\SWEEP_2026_01_05_08_49_25\\IMG_49.75\\TEMP_54"
    #VIPA_subtraction(sweepFolder, preserve_noise = False)
    VIPA_temp_sidebysides(sweepFolder)
    #VIPA_show_ONOFF(imageFolder)
