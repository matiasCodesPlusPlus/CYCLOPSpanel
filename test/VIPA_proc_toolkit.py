"""A collection of methods for use in processing and reducing data for CYCLOPS-VIPA"""
import numpy as np
import os
import matplotlib.pyplot as plt
import csv

from scipy.signal import fftconvolve
from scipy.ndimage import shift
from numpy.linalg import norm


def track_qcl_beam(
    cropped,
    kernel,
    x_prev=None,
    search_left=30,
    search_right=3,
    show_plot=True,
):

    # flatten
    profile = cropped.sum(axis=0).astype(float) #flatten that shit
    profile -= profile.mean()

    # convolution
    corr = fftconvolve(profile, kernel[::-1], mode="same") #kernel has to be flipped SUM(p[E]k[E-x]) vs SUM(p[E]k[x-E])
    #at what x pos does measured profile most closely resemble input gaussian
    #IF WE DONT FLIP HERE IT PENALIZES THE RIGHT SIDE NOT THE LEFT

    # find peaks
    if x_prev is None:
        x_peak = np.argmax(corr)
    else:
        lo = max(0, int(x_prev - search_left))
        hi = min(len(corr), int(x_prev + search_right))
        x_peak = lo + np.argmax(corr[lo:hi])

    #subpixel refined
    x_refined = float(x_peak)
    if 1 < x_peak < len(corr) - 2:
        y0, y1, y2 = corr[x_peak - 1], corr[x_peak], corr[x_peak + 1]
        denom = (np.log(y0) - 2*np.log(y1) + np.log(y2))
        if denom != 0:
            x_refined += (np.log(y0) - np.log(y2)) / (2 * denom)

    #plotting
    if show_plot:
        x = np.arange(len(profile))

        fig, ax = plt.subplots(2, 1, sharex=True, figsize=(10, 6))

        ax[0].plot(x, profile / np.max(np.abs(profile)), label="Profile")
        ax[0].axvline(x_refined, color="r", linestyle="--", label="Beam")
        ax[0].set_ylabel("Normalized intensity")
        ax[0].legend()
        ax[0].grid(True)

        ax[1].plot(x, corr / np.max(np.abs(corr)), label="Correlation")
        ax[1].axvline(x_refined, color="r", linestyle="--")
        ax[1].set_ylabel("Normalized response")
        ax[1].set_xlabel("X pixel (cropped)")
        ax[1].legend()
        ax[1].grid(True)

        plt.tight_layout()
        plt.show()

    return x_refined, corr

def VIPA_subtraction(sweepFolder, preserve_noise = True, testMode = "temp"):
    """
    VIPA_subtraction will run through an entire test folder and produce subtracted images and reverse subtracted image. Optional kwarg to remove noise
    
    :param sweepFolder: Directory of test
    :param preserve_noise: bool, subtract average background?
    :param testMode: string, opt("temp", "voltage")
    """
    if testMode == "temp":  
        with os.scandir(f"{sweepFolder}") as TEMPS:
            for TEMP in TEMPS: #running down dirs
                if TEMP.is_dir():

                    with open(f"{sweepFolder}\\{TEMP.name}\\imageON.csv") as file:
                        reader = csv.reader(file)
                        ONimage = list(reader)
                    with open(f"{sweepFolder}\\{TEMP.name}\\imageOFF.csv") as file:
                        reader = csv.reader(file)
                        OFFimage = list(reader)

                    ONimage = np.array(ONimage, dtype = float)
                    OFFimage = np.array(OFFimage, dtype = float)
                    #ONimage = np.fliplr(np.loadtxt(f"{sweepFolder}\\{LOC.name}\\{TEMP.name}\\imageON.csv", delimiter=","))
                    #OFFimage = np.fliplr(np.loadtxt(f"{sweepFolder}\\{LOC.name}\\{TEMP.name}\\imageON.csv", delimiter=","))
                    fsys_topdown = f"{sweepFolder}\\{TEMP.name}"
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
    elif testMode == "voltage":
        with os.scandir(sweepFolder) as volts:
            for volt in volts:
                if volt.is_dir():
                    

                    with open(f"{sweepFolder}\\{volt.name}\\imageON.csv") as file:
                        reader = csv.reader(file)
                        ONimage = list(reader)
                    with open(f"{sweepFolder}\\{volt.name}\\imageOFF.csv") as file:
                        reader = csv.reader(file)
                        OFFimage = list(reader)

                    ONimage = np.array(ONimage, dtype = float)
                    OFFimage = np.array(OFFimage, dtype = float)
                    #ONimage = np.fliplr(np.loadtxt(f"{sweepFolder}\\{LOC.name}\\{TEMP.name}\\imageON.csv", delimiter=","))
                    #OFFimage = np.fliplr(np.loadtxt(f"{sweepFolder}\\{LOC.name}\\{TEMP.name}\\imageON.csv", delimiter=","))
                    fsys_topdown = f"{sweepFolder}\\{volt.name}"
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

def VIPA_imageFlatten(image):
    IMAGE_FLAT = np.sum(image, axis = 0)
    IMAGE_FLAT = VIPA_cameraBaffleMask(IMAGE_FLAT)
    return IMAGE_FLAT

def VIPA_voltage_sidebysides(testFolder):
    #file navigation, polarity testing and sorting
    TOTAL_VOLTAGES = []
    TOTAL_IMAGES = []
    TOTAL_IMAGES_CROPPED = []
    with os.scandir(testFolder) as VOLTS:
        for VOLT in VOLTS:
            localVoltage = float(str(VOLT.name).split("_")[1])
            localIMAGE = np.fliplr(np.loadtxt(f"{testFolder}\\{VOLT.name}\\imageSUB.csv", delimiter=","))
            localIMAGE_rev = np.fliplr(np.loadtxt(f"{testFolder}\\{VOLT.name}\\imageSUB_rev.csv", delimiter=","))
            IMAGE = VIPA_polarity(localIMAGE,localIMAGE_rev)
            TOTAL_VOLTAGES.append(localVoltage)
            TOTAL_IMAGES.append(IMAGE)
            TOTAL_IMAGES_CROPPED.append(IMAGE[35:223, 17:367])
        TOTAL_IMAGES = np.array(TOTAL_IMAGES)
        TOTAL_VOLTAGES = np.array(TOTAL_VOLTAGES)
        TOTAL_IMAGES_CROPPED = np.array(TOTAL_IMAGES_CROPPED)
        sorted_idx = np.argsort(TOTAL_VOLTAGES)
        TOTAL_VOLTAGES = TOTAL_VOLTAGES[sorted_idx]
        TOTAL_IMAGES = TOTAL_IMAGES[sorted_idx]
        TOTAL_IMAGES_CROPPED = TOTAL_IMAGES_CROPPED[sorted_idx]
    #plotting
    #TOTAL_IMAGES= np.reshape(TOTAL_IMAGES, (3,3,288,384))
    #TOTAL_VOLTAGES = np.reshape(TOTAL_VOLTAGES,(3,3))
    cmin = np.min(TOTAL_IMAGES_CROPPED)
    cmax = np.max(TOTAL_IMAGES_CROPPED)
    #fig, ax = plt.subplots(1,3)
    fig2, ax2 = plt.subplots(1,len(TOTAL_IMAGES))


    # for ind, image in np.ndenumerate(TOTAL_IMAGES[:,:,0,0]):
        
    #     i, j = ind
    #     ax[i,j].imshow((TOTAL_IMAGES[i,j]), cmap = "jet", vmin = cmin, vmax = cmax)
    #     ax[i,j].set_title(f"{round(TOTAL_VOLTAGES[i,j],3)} Volts")


    for i in range(0,len(TOTAL_VOLTAGES)):
        
        fig2.suptitle("Changing QCL switching frequency")
        ax2[i].imshow(TOTAL_IMAGES_CROPPED[i], cmap = "jet", vmin = cmin, vmax = cmax)
        ax2[i].set_title(f"{TOTAL_VOLTAGES[i]} Hz")
        #ax2[i].plot(TOTAL_IMAGES_CROPPED[i].sum(axis = 0))
        
    # np.savetxt("background_image.csv", TOTAL_IMAGES_CROPPED[1], delimiter=",")
    plt.show()
    return TOTAL_IMAGES_CROPPED, TOTAL_VOLTAGES

def VIPA_cameraBaffleMask(image):
    """
    Creates a boolean circular mask for a 2D array.

    Parameters:
    h (int): Height of the array.
    w (int): Width of the array.
    center (tuple, optional): (x, y) coordinates of the center. Defaults to the middle.
    radius (int, optional): Radius of the circle. Defaults to the smallest distance 
                            between the center and image walls.

    Returns:
    numpy.ndarray: A 2D boolean array (mask).
    """
    h = 288
    w = 384
    center = None
    radius = 110

    if center is None:
        center = (int(w/2), int(h/2))
    if radius is None:
        radius = min(center[0], center[1], w - center[0], h - center[1])

    # Create a grid of coordinates
    Y, X = np.ogrid[:h, :w]
    
    # Calculate the distance of all points from the center
    dist_from_center = np.sqrt((X - center[0])**2 + (Y - center[1])**2)
    
    # Create the mask where distance is less than or equal to the radius
    mask = dist_from_center <= radius
    return np.array(image*mask, dtype = float)
    
def VIPA_kernelGeneration(bright_image, background_image, imagearray, valuearray):
    """
    Docstring for VIPA_kernelGeneration
    
    :param bright_image: bright image to use in kernel generation
    :param background_image: background image to use in subtraction
    :param imagearray: array of images, ordered by :param valuearray
    :param valuearray: descriptor value, going to be a voltage or temp @ static x position
    """
    kernel = bright_image - background_image #build kernel based on brightest image
    kernel -= bright_image.mean()
    #normalize kernel
    kernel /= np.linalg.norm(kernel)

    peaks = []

    for frame in imagearray:
        frame_cleaned = frame - background_image
        frameCORR = fftconvolve(frame_cleaned, kernel[::-1,::-1], mode = "same")
        ypeak, xpeak = np.unravel_index(np.argmax(frameCORR), frameCORR.shape)
        peaks.append(np.array([xpeak, ypeak]))


    imagearray_no_background = np.array(imagearray_no_background, dtype = float)


    


    return kernel


def VIPA_matchFilter2D(cropped_frames, background_image, testVals, testMode = "voltage"):
    #define some shit locally to handle pre proc
    def cleanFrame(image,background_image):
        return image - background_image
    def buildKernel(bright_image, background_image):
        kernel = bright_image - background_image
        kernel-= kernel.mean()
        kernel /= np.linalg.norm(kernel)
        ky, kx = np.unravel_index(np.argmax(kernel), kernel.shape)

        
        dy = -(ky - kernel.shape[0]//2)
        dx = -(kx - kernel.shape[1]//2)
        kernel = shift(kernel, shift=(dy, dx), order=1)
        return kernel
    
    cleaned_Frames = []
    print(f"cropped shape array: {cropped_frames.shape}")
    for image in cropped_frames:
        cleaned_Frames.append(image)
    cleaned_Frames = np.array(cleaned_Frames)


    bright_idx = -2#brightest_frame_index(cleaned_Frames)
    bright_frame = cleaned_Frames[bright_idx]
    kernel = buildKernel(bright_frame, background_image)

    x_peaks = []
    y_peaks = []
    for image in cleaned_Frames:
        
        image-= image.mean()
        image /= np.linalg.norm(image)
        #image = image - background_image
        corr = fftconvolve(
            image,
            kernel[::-1, ::-1],
            mode = "same"
        )
        
        y_peak, x_peak = np.unravel_index(np.argmax(corr), corr.shape)
        x_peaks.append(x_peak)
        y_peaks.append(y_peak)
    cmin = np.min(cleaned_Frames)
    cmax = np.max(cleaned_Frames)
    x_peaks = np.array(x_peaks)
    y_peaks = np.array(y_peaks)
    #plot dx/dv, dy/dv---------------------------------------------------------------------------
    fig, ax = plt.subplots(1,2, sharey=True)

    slope, yint = np.polyfit(testVals, x_peaks, 1)
    fitVals = slope*testVals + yint

    slopeY, yintY = np.polyfit(testVals, y_peaks, 1)
    fitValsY = slopeY * testVals + yintY

    ax[0].plot(testVals,x_peaks)
    ax[0].plot(testVals,fitVals, color = "red", linestyle = "--")
    ax[1].plot(testVals, y_peaks)
    ax[1].plot(testVals,fitValsY, color = "red", linestyle = "--")
    ax[0].set_title(f"dx/dV = {round(slope*35, 2)} micron/Volts")
    ax[1].set_title(f"dy/dV = {round(slopeY*35, 2)} micron/Volts")
    #plot targets----------------------------------------------------------------------------
    fig2, ax2 = plt.subplots(1, len(testVals))
    for i in range(0,len(testVals)):
        ax2[i].imshow(cleaned_Frames[i],cmap = "jet", vmin = cmin, vmax = cmax)
        ax2[i].axvline(x_peaks[i], color = "red", linestyle = '--')
        ax2[i].axhline(y_peaks[i], color = "red", linestyle = '--')
        ax2[i].set_title(f"{round(testVals[i],2)} volts")
    #show kernel image-----------------------------------------------------------------------
    fig3, ax3 = plt.subplots(1,1)
    ax3.imshow(cleaned_Frames[bright_idx], cmap = "jet")
    plt.show()

def VIPA_temp_sidebysides_indev(testFolder):
    #file navigation, polarity testing and sorting
    TOTAL_TEMPS = []
    TOTAL_IMAGES = []
    TOTAL_IMAGES_CROPPED = []
    with os.scandir(testFolder) as TEMPS:
        for TEMP in TEMPS:
            localTemp = float(str(TEMP.name).split("_")[1])
            localIMAGE = np.fliplr(np.loadtxt(f"{testFolder}\\{TEMP.name}\\imageSUB.csv", delimiter=","))
            localIMAGE_rev = np.fliplr(np.loadtxt(f"{testFolder}\\{TEMP.name}\\imageSUB_rev.csv", delimiter=","))
            IMAGE = VIPA_polarity(localIMAGE,localIMAGE_rev)
            TOTAL_TEMPS.append(localTemp)
            TOTAL_IMAGES.append(IMAGE)
            TOTAL_IMAGES_CROPPED.append(IMAGE[35:223, 17:367])
        TOTAL_IMAGES = np.array(TOTAL_IMAGES)
        TOTAL_TEMPS = np.array(TOTAL_TEMPS)
        TOTAL_IMAGES_CROPPED = np.array(TOTAL_IMAGES_CROPPED)
        sorted_idx = np.argsort(TOTAL_TEMPS)
        TOTAL_TEMPS = TOTAL_TEMPS[sorted_idx]
        TOTAL_IMAGES = TOTAL_IMAGES[sorted_idx]
        TOTAL_IMAGES_CROPPED = TOTAL_IMAGES_CROPPED[sorted_idx]
    #plotting
    #TOTAL_IMAGES= np.reshape(TOTAL_IMAGES, (3,3,288,384))
    #TOTAL_VOLTAGES = np.reshape(TOTAL_VOLTAGES,(3,3))
    cmin = np.min(TOTAL_IMAGES_CROPPED)
    cmax = np.max(TOTAL_IMAGES_CROPPED)
    #fig, ax = plt.subplots(1,3)
    fig2, ax2 = plt.subplots(1,len(TOTAL_IMAGES))


    # for ind, image in np.ndenumerate(TOTAL_IMAGES[:,:,0,0]):
        
    #     i, j = ind
    #     ax[i,j].imshow((TOTAL_IMAGES[i,j]), cmap = "jet", vmin = cmin, vmax = cmax)
    #     ax[i,j].set_title(f"{round(TOTAL_VOLTAGES[i,j],3)} Volts")

    imshow_ims = []
    for i in range(0,len(TOTAL_TEMPS)):
        fig2.suptitle("Changing QCL switching freq")
        image = ax2[i].imshow(TOTAL_IMAGES_CROPPED[i], cmap = "jet", vmin = cmin, vmax = cmax)
        plt.colorbar(image, shrink = .125)
        ax2[i].set_title(f"{TOTAL_TEMPS[i]} Hz")
        #ax2[i].plot(TOTAL_IMAGES_CROPPED[i].sum(axis = 0))
    # np.savetxt("background_image.csv", TOTAL_IMAGES_CROPPED[1], delimiter=",")
    plt.show()
    return TOTAL_IMAGES_CROPPED, TOTAL_TEMPS

if __name__ == "__main__":
    sweepFolder = "D:\\VIPA_TEST_DATA\\FREQ_SWEEP_2026_01_12_13_59_51"
    #LOCFolder = "D:\\VIPA_TEST_DATA\\SWEEP_2026_01_05_08_49_25\\IMG_49.75"
    #imageFolder = "D:\\VIPA_TEST_DATA\\SWEEP_2026_01_05_08_49_25\\IMG_49.75\\TEMP_54"
    VIPA_subtraction(sweepFolder, preserve_noise = False, testMode = "temp")

    cropped_frames, temps = VIPA_temp_sidebysides_indev(sweepFolder) #retrieve processed frames
    
    background_image = np.loadtxt("background_image.csv", dtype=float, delimiter=",")
    
    VIPA_matchFilter2D(cropped_frames, background_image, temps)

    #VIPA_temp_sidebysides(sweepFolder)
    # x_prev = None

    # for cropped in cropped_frames:
    #     x, corr = track_qcl_beam(
    #         cropped,
    #         kernel,
    #         x_prev=x_prev,
    #         show_plot=True,   
    #     )
    #     x_prev = x
    
