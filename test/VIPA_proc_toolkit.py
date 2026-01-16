"""A collection of methods for use in processing and reducing data for CYCLOPS-VIPA"""
import numpy as np
import os
import matplotlib.pyplot as plt
import csv

from scipy.signal import fftconvolve
from scipy.ndimage import shift
from numpy.linalg import norm
import scipy.sparse.linalg as spla
import scipy.sparse as sp

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

                    ONimage = np.fliplr(np.array(ONimage, dtype = float))
                    OFFimage = np.fliplr(np.array(OFFimage, dtype = float))
                    #ONimage = np.fliplr(np.loadtxt(f"{sweepFolder}\\{LOC.name}\\{TEMP.name}\\imageON.csv", delimiter=","))
                    #OFFimage = np.fliplr(np.loadtxt(f"{sweepFolder}\\{LOC.name}\\{TEMP.name}\\imageON.csv", delimiter=","))
                    fsys_topdown = f"{sweepFolder}\\{TEMP.name}"
                    if preserve_noise == True:
                        SUBimage = (ONimage-OFFimage)
                        SUBimage_rev = (OFFimage-ONimage)
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

                    ONimage = np.fliplr(np.array(ONimage, dtype = float))
                    OFFimage = np.fliplr(np.array(OFFimage, dtype = float))
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
        ax[i,j].imshow(TOTAL_IMAGES[i,j], cmap = "jet", vmin = cmin, vmax = cmax)
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

    ax[0].plot(testVals,x_peaks*35)
    ax[0].plot(testVals,fitVals*35, color = "red", linestyle = "--")
    ax[1].plot(testVals, y_peaks*35)
    ax[1].plot(testVals,fitValsY*35, color = "red", linestyle = "--")
    ax[0].set_xlabel("Voltage Input (V)")
    ax[1].set_xlabel("Voltage Input (V)")
    ax[0].set_ylabel("Position (um)")
    ax[1].set_ylabel("Position (um)")
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
            localIMAGE = (np.loadtxt(f"{testFolder}\\{TEMP.name}\\imageSUB.csv", delimiter=","))
            localIMAGE_rev = (np.loadtxt(f"{testFolder}\\{TEMP.name}\\imageSUB_rev.csv", delimiter=","))
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
    

    #TOTAL_IMAGES_CROPPED, TOTAL_TEMPS, div = plotReshape(TOTAL_IMAGES_CROPPED, TOTAL_TEMPS)
    
    # fig, ax = plt.subplots(div,TOTAL_TEMPS.shape[1])
    # for ind, image in np.ndenumerate(TOTAL_IMAGES_CROPPED[:,:,0,0]):
        
    #     i, j = ind
    #     ax[i,j].imshow((TOTAL_IMAGES_CROPPED[i,j]), cmap = "jet", vmin = cmin, vmax = cmax)
    #     ax[i,j].set_title(f"{round(TOTAL_TEMPS[i,j],3)} deg")

    # imshow_ims = []
    # for i in range(0,len(TOTAL_TEMPS)):
    #     fig2.suptitle("Changing QCL switching phase")
    #     image = ax2[i].imshow(TOTAL_IMAGES_CROPPED[i], cmap = "jet", vmin = cmin, vmax = cmax)
    #     plt.colorbar(image, shrink = .125)
    #     ax2[i].set_title(f"{TOTAL_TEMPS[i]} deg")
    #     #ax2[i].plot(TOTAL_IMAGES_CROPPED[i].sum(axis = 0))
    # # np.savetxt("background_image.csv", TOTAL_IMAGES_CROPPED[1], delimiter=",")
    #plt.show()
    return TOTAL_IMAGES_CROPPED, TOTAL_TEMPS

def plotReshape(image_array, data_array):
    allowable_divisors = []
    for n in range(2,4):
        if len(data_array) % n == 0:
            allowable_divisors.append(n)
    allowable_divisors = np.array(allowable_divisors, dtype = int)
    div = allowable_divisors.max()
    if len(allowable_divisors) != 0:
        image_array = np.reshape(image_array,(int(div),int(len(data_array)/div), 188, 350))
        data_array = np.reshape(data_array, (div,int(len(data_array)/div)))
        return image_array, data_array, div
    else:
        return image_array, data_array, div

def overlap_correction(images, overlaps, axis=1):
    """
    Adjust images to minimize seams in overlaps.

    Parameters
    ----------
    images : list of np.ndarray
        List of corrected images to be stitched in sequence.
    overlaps : list of int
        Overlap sizes (pixels) between consecutive images.
    axis : int
        Axis along which to stitch (0=vertical, 1=horizontal).
    """
    adjusted = [images[0].copy()]  # first image stays as reference
    
    for i, (img, ov) in enumerate(zip(images[1:], overlaps)):
        ref = adjusted[-1]
        
        if axis == 1:  # horizontal stitching
            ref_overlap = ref[:, -ov:]
            img_overlap = img[:, :ov]
            
        delta = np.mean(ref_overlap - img_overlap)
        
        # shift current image by delta
        adjusted.append(img + delta)
    
    return adjusted

def baseline_correct(images_on, edge_rows=50, method="median"):
    """
    Baseline correction with drift estimated from edge rows,
    smoothed strongly to avoid seams in signal regions.
    """
    images = [img.copy() for img in images_on]  # avoid modifying in-place
    
    for i in range(len(images) - 1):
        last_col = images[i][:, -3]
        first_col = images[i+1][:, 2]
        
        avg_col = (last_col + first_col) / 2.0
        
        images[i][:, -1]   = avg_col
        images[i+1][:, 0]  = avg_col
    
    images_on = np.array(images,dtype = float)
    print(images_on.shape)

    #
    top = images_on[:, :edge_rows, :]
    bottom = images_on[:, -edge_rows:, :]
    edge_pixels = np.concatenate([top, bottom], axis=1)

    
    if method == "median":
        baselines = np.median(edge_pixels, axis=(1, 2))
    elif method == "mean":
        baselines = np.mean(edge_pixels, axis=(1, 2))
    else:
        baselines = np.percentile(edge_pixels, 5, axis=(1, 2))

    drift_model=baselines
    drift_model = drift_model - np.median(baselines)

    
    corrected = images_on - drift_model[:, None, None]

    return corrected, baselines, drift_model

def create_circular_mask(h, w, center=None, radius=None):
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
    return mask


def readMetaData(path):
    data_dict = {}
    
    with open(f"{path}\\image_metaData.txt", "r") as file:
        lines = []
        for line in file:
            lines.append(file.readlines())
        print(lines)
        for line in lines[2:]:
            print(line)
            data_dict[line.split(", ")[0]] = float(line.split(", ")[1])
    return data_dict

def stitch_images(filePath, overlaps, baffle = False, blend = False):

    """
    Args:
        filePath: path to directory containing image subdirectories
        overlaps: list of overlap amounts between images in x-direction  
        baffle: whether to apply a circular mask to the images (default: False)
        blend: whether to blend overlapping regions (default: False)
    Returns:
        stitched image as 2D numpy array
        stitched_ones: 2D numpy array of ones with same shape as stitched image
        start: minimum distance
        stop: maximum distance
    """
    images = []
    images_COMP_OFF = []
    dists = []
    _noise_vars = []
    offims = []
    with os.scandir(filePath) as dirs:
            
            for dir in dirs:

                if dir.is_dir():
                    print(str(dir.name).split("_")[1])
                    dist = str(dir.name).split("_")[1]
                    dists.append(dist)
                    #imageset = vipaIMAGE(f"{filePath}\\{dir.name}",f"{filePath}\\{dir.name}\\imageON.csv", f"{filePath}\\{dir.name}\\imageOFF.csv",rev=False)
                    with open(f"{filePath}\\{dir.name}\\imageSUB.csv") as on_path:
                    
                        reader_on = csv.reader(on_path)
                        data_on = (np.array(list(reader_on), dtype = float))
                        image = data_on
                        on_path.close()
                    with open(f"{filePath}\\{dir.name}\\imageSUB_rev.csv") as on_path2:
                    
                        reader_on = csv.reader(on_path2)
                        data_on = (np.array(list(reader_on), dtype = float))
                        image2 = data_on
                        on_path2.close()

                    images.append(VIPA_polarity(image, image2))

                    with open(f"{filePath}\\{dir.name}\\imageOFF.csv") as off_path:
                        reader_off = csv.reader(off_path)
                        data_off = (np.array(list(reader_off), dtype = float))
                        offims.append(data_off)
                        on_path.close()
                
                    # with open(f"{filePath}\\{dir.name}\\compressedImageOFF_0.csv") as on_path:
                    
                    #     reader_on = csv.reader(on_path)
                    #     data_on = np.fliplr(list(reader_on))
                    #     images_COMP_OFF.append(data_on[:,48:336])
                    #     on_path.close()
            mask = create_circular_mask(288,384,None,110)   
            offims = np.array(offims, dtype = float)
            variances, H, W = estimate_noise_variance2(offims)
            _noise_vars.append(variances)
                


                    # with open(f"{filePath}\\{dir.name}\\compressedImageOFF_0.csv") as on_path:
                    #     reader_off = csv.reader(on_path)
                    #     data_off = np.fliplr(list(reader_off))
                    #     offims.append(data_off)
                    
                    
    

    variances = (np.mean(np.array(_noise_vars, dtype = float), axis = 0))
    print(np.shape(variances))
    dists = np.array(dists, dtype = 'float')
    sorted_indices = dists.argsort()
    dists = dists[sorted_indices]
    images = np.array(images, dtype = 'float')[sorted_indices]
    #images_off = np.array(images_COMP_OFF, dtype = float)[sorted_indices]
    images,_,_ = baseline_correct(images)
    #images = overlap_correction(images,overlaps)
    #offims = np.array(offims, dtype = 'float')[sorted_indices]
    # Compute per-pixel noise variances 
    #pixel_variances, H, W_total = estimate_noise_variance2(offims)
    # index pixels to their location in stitched map
    W_total = sum(image.shape[1] for image in images) - sum(overlaps)
    def map_pixel_index(y, x): return y * W_total + x

    data = []
    rows = []
    cols = []
    weights = []
    x_offset = 0
    if blend == False:
        #this is the default, using blended weights instead of 1/var LOOKS BETTER but is not statistically correct
        #ALL OF THIS IS TO CALCULATE W, (weights matrix) and A (pointing matrix)-------------------------------------
        for i, img in enumerate(images):
            h, w = img.shape
            for y in range(h):
                for x in range(w):
                    map_x = x + x_offset #update current x position in stitched map
                    map_idx = map_pixel_index(y, map_x) #get index of pixel in stitched map

                    pixel_val = img[y, x] #get pixel value
                    data.append(pixel_val) 

                    row = len(data) - 1
                    col = map_idx
                    rows.append(row)
                    cols.append(col)

                    var = variances[y*w+x] #get variance, default to small value if key not found
                    if var != 0:
                        weights.append(1.0/var) #weight is inverse of variance
                    else:
                        weights.append(1.0e-10)

            if i < len(overlaps):
                x_offset += (w-overlaps[i]) #update x position for next image, accounting for overlap
            else:
                x_offset += w

        d = np.array(data) #observation vector of all pixel values from all images
        W = sp.diags(weights) #weight matrix, THIS DOES NOT ACCOUNT FOR COVARIANCES
        d_ones = np.ones_like(d)
        #build A matrix
        try:
            A = sp.coo_matrix((np.ones_like(rows), (rows, cols)), shape=(len(data), H * W_total))
        except ValueError:
            A = sp.coo_matrix((np.ones_like(rows), (rows, cols)), shape=(len(data), H * W_total))
        #-------------------------------------------------------------------------------------------------------------
        # Build matrices
        d_ones = np.ones_like(data)
        
    
    
    # Solving linear system
    AT_W = A.T @ W # A^T * W
    ATA = AT_W @ A # A^T * W * A
    ATd = AT_W @ d # A^T * W * d 
    ATd_ones = AT_W@ d_ones

    m = spla.spsolve(ATA, ATd) #solve for map`
    ans= (spla.lsqr(A,d_ones)) #solve for map of ones
    
    m_ones = ans[0]
    print(m_ones)
    stitched_ones = m_ones.reshape((H,W_total))
    stitched = m.reshape((H, W_total))
    return (stitched),stitched_ones, np.min(dists), np.max(dists)

def estimate_noise_variance2(images):
    """
    Estimate per-pixel noise variances in the stitched map space.
    Args:
        images: list of 2D numpy arrays 
        overlaps: list of overlap amounts between images in x-direction
    Returns:
        variances: dict mapping pixel indices in map space to estimated noise variances
        H: image height
        W_total: total width of stitched image"""

    H = images[0].shape[0]
    W = images[0].shape[1]
    N_images = images.shape[0]

    pixel_values = np.zeros((H * W, N_images))

    for i, img in enumerate(images):
        h, w = img.shape
        for y in range(h):
            for x in range(w):
                idx = y * W + x
                pixel_values[idx,i] = img[y, x]

    # # Calculate variance, using small floor to avoid divide-by-zero
    # variances = {idx: np.var(vals, ddof=1) if len(vals) > 1 else 1e-1
    #              for idx, vals in pixel_values.items()}
    

    variances = np.std(pixel_values,axis =1)**2

        
    return variances, H, W

if __name__ == "__main__":

    #print(readMetaData("D:\\VIPA_TEST_DATA\\PHASE_SWEEP_2026_01_14_14_35_50\\PHASE_90.0"))
    # sweepFolder = "D:\\VIPA_TEST_DATA\\PHASE_SWEEP_2026_01_13_14_32_50"
    # VIPA_subtraction(sweepFolder, preserve_noise = False, testMode = "temp")
    # cropped_frames, temps = VIPA_temp_sidebysides_indev(sweepFolder) #retrieve processed frames
    
    # sweepFolder2 = "D:\\VIPA_TEST_DATA\\PHASE_SWEEP_2026_01_14_09_13_34"
    # VIPA_subtraction(sweepFolder2, preserve_noise = False, testMode = "temp")
    # cropped_frames2, temps2 = VIPA_temp_sidebysides_indev(sweepFolder2)

    # sweepFolder3= "D:\\VIPA_TEST_DATA\\PHASE_SWEEP_2026_01_14_10_47_42"
    # VIPA_subtraction(sweepFolder3, preserve_noise = False, testMode = "temp")
    # cropped_frames3, temps3 = VIPA_temp_sidebysides_indev(sweepFolder3)


    # sweepFolder4 ="D:\VIPA_TEST_DATA\PHASE_SWEEP_2026_01_14_11_25_39"
    # VIPA_subtraction(sweepFolder4, preserve_noise = False, testMode = "temp")
    # cropped_frames4, temps4 = VIPA_temp_sidebysides_indev(sweepFolder4)

    # sweepFolder5 ="D:\\VIPA_TEST_DATA\\PHASE_SWEEP_2026_01_14_13_46_21"
    # VIPA_subtraction(sweepFolder5, preserve_noise = False, testMode = "temp")
    # cropped_frames5, temps5 = VIPA_temp_sidebysides_indev(sweepFolder5)

    

    # sweepFolder6 = "D:\\VIPA_TEST_DATA\\PHASE_SWEEP_2026_01_14_14_35_50"
    # VIPA_subtraction(sweepFolder6, preserve_noise = False, testMode = "temp")
    # cropped_frames6, temps6 = VIPA_temp_sidebysides_indev(sweepFolder6)

    #sideBySide_ims = np.array([cropped_frames[-1,:,:], cropped_frames2[0,:,:], cropped_frames3[0,:,:], cropped_frames4[0,:,:], cropped_frames5[0,:,:], cropped_frames6[0,:,:]])
    #sideBySide_vals = np.array([temps[-1], temps2[0], temps3[0], temps4[0], temps5[0], temps6[0]])

    #cmin = np.min(sideBySide_ims)
    #cmax = np.max(sideBySide_ims)

    # fig, ax = plt.subplots(1,len(sideBySide_vals))
    # for i in range(0,len(sideBySide_vals)):
    #     ax[i].imshow(sideBySide_ims[i], cmap = "jet", vmin = cmin, vmax = cmax)
    #     ax[i].set_title(f"{sideBySide_vals[i]} deg")
    #map,map1s, min, max = stitch_images("D:\\VIPA_TEST_DATA\\SWEEP_2026_01_15_15_20_43", overlaps = np.full(19,100))


    sweepFolder = "D:\\VIPA_TEST_DATA\\SWEEP_2026_01_15_15_20_43"
    VIPA_subtraction(sweepFolder, preserve_noise = False, testMode = "temp")
    map,map1s, min, max = stitch_images("D:\\VIPA_TEST_DATA\\SWEEP_2026_01_15_15_20_43", overlaps = np.full(19,234))
    extent = [min*1000,max*1000, 288*35, 0]
    fig, ax = plt.subplots()
    map = ax.imshow(map, cmap = "jet", extent=extent)
    plt.colorbar(map)
    plt.show()

    # cropped_frames, temps = VIPA_temp_sidebysides_indev(sweepFolder) #retrieve processed frames
    
    # background_image = np.loadtxt("background_image.csv", dtype=float, delimiter=",")
    
    # VIPA_matchFilter2D(cropped_frames[2:5,:,:], background_image, temps[2:5])

    
