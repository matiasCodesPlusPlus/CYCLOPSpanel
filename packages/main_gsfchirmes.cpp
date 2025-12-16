#include <iostream>

#include <C:\CYCLOPSpanel\packages\GlobalDef.h>
#include <C:\CYCLOPSpanel\packages\MICROXCAM-384I_CAPI.h>
#include <chrono>
#include <stdio.h>
#include <string.h>
#include <filesystem>
#include <fstream>
#include <vector>
#include <C:\Program Files (x86)\IVI Foundation\VISA\WinNT\Include\visa.h>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <cmath>
#include <thread>
//USE THIS FILE TO MAKE CHANGES TO DLL FILE FOR ALL OTHER PROJECTS USING INO CAMERA
//Please don't mess with any of this code without asking me first because many things will break -Matias
using namespace std;

#define DLLEXPORT extern "C" __declspec(dllexport)

int qclStatus = false;
float* aImageDataRAW_comp_global_on = (float*)malloc(sizeof(float)*384*288);
float* aImageDataRAW_comp_global_off = (float*)malloc(sizeof(float)*384*288);
std::byte* aImageDataDisplay_comp_global = (std::byte*)malloc(sizeof(std::byte)*384*288);
int image_counter_global = 0;


using Frame = float[288][384];
using offsetFrame =  unsigned short[288][384];


offsetFrame offsetbuffer;
Frame bufferA;
Frame bufferB;

offsetFrame* ofb = &offsetbuffer;
Frame* writeBuffer = &bufferA;
Frame* readBuffer = &bufferB;

mutex mtx;
condition_variable cv;
atomic<bool> newFrameAvailable(false);

//frame accumulation
vector<double> accumOn(384*288, 0.0);
vector<double> accumOff(384*288, 0.0);


string csvPathOn;
string csvPathOff;
std::atomic<uint64_t> frameSeq{0};

DLLEXPORT int init_camera(bool OFFSET) {
    
        const char* dllPath = "C:\\CYCLOPSpanel\\bin"; 
        char* pstrPath= const_cast<char*>(dllPath);
        cout<<"DETECTED CAMERAS: "<<fn_DetectCamera(pstrPath)<<endl;
        const char* cam_IP_const = fn_GetDetectedCameraIP(0); 
        char* cam_IP = const_cast<char*>(cam_IP_const);
        cout<<cam_IP<<endl;
    
        int init_error = fn_Initialize(cam_IP,false,pstrPath);
        cout<<"INIT ERROR: "<<fn_ErrorToText(init_error)<<endl;
    
    

    
    return 0;
    

}

DLLEXPORT void camera_image(char* filename, bool init, int RAWPROC) {

    int iHeight = 288;
    int iWidth = 384;
    int iImageSize = iHeight*iWidth;
    float* aImageDataRAW;
    std::byte* aImageDataDisplay;
    int RAW_PROC_ERROR = fn_SetRAWProcessOption(RAWPROC);
    //unsigned short* aImageOffsetData;

    aImageDataRAW = (float*)malloc(sizeof(float)*iImageSize);
    aImageDataDisplay = (std::byte*)malloc(sizeof(std::byte)*iImageSize);
    //aImageOffsetData = (unsigned short*)malloc(sizeof(unsigned short)*iImageSize);
    
    //cout<<pstrPath<<endl;

    //cout<<cam_IP_const<<endl;

    int size_error = fn_GetImageSize(iWidth, iHeight);
    

    
    //cout<<"size error: "<<fn_ErrorToText(size_error)<<endl;
    //cout<<"raw process error: "<< fn_ErrorToText(RAW_PROC_ERROR) << endl;
    int camera_error = fn_GetCameraImage(aImageDataRAW,aImageDataDisplay,iImageSize);
    ofstream outfile; ofstream outfile2;

    //const char* filename = "C:\\Users\\gsfchirmes\\Desktop\\CYCLOPS_VIPA_CONTROL_PANEL2\\trigger_image.csv";
    
    outfile.open(filename);

    int rows = 288;
    int cols = 384;
    vector<vector<int>> ImageDataRAW(rows, vector<int>(cols));
    int index = 0;
    for(int i = 0;i<rows;i++) {
        for(int j = 0; j< cols; j++){
            ImageDataRAW[i][j] = aImageDataRAW[index++];
        }
    }
    free(aImageDataRAW);
    free(aImageDataDisplay);
    for(const auto &row : ImageDataRAW) {
        for (size_t i = 0; i < row.size(); ++i) {
            outfile << row[i];
            if (i != row.size() - 1) {
                outfile << ",";
            }
        }
        outfile << "\n";
    }
    outfile.close();
    


}

DLLEXPORT float* cameraSpamAvg(char* filename, bool init, int numPics) {

    int iHeight = 288;
    int iWidth = 384;
    int iImageSize = iHeight*iWidth;
    
    //Initializing compiled data arrays and allocating needed memory to them
    float* aImageDataRAW_comp;
    std::byte* aImageDataDisplay_comp;
    aImageDataRAW_comp = (float*)malloc(sizeof(float)*iImageSize);
    aImageDataDisplay_comp = (std::byte*)malloc(sizeof(std::byte)*iImageSize);

    //init all elements as zero
    for (int i = 0; i < (iImageSize); i++) {
        aImageDataRAW_comp[i] = 1.0f;
    }
    //casting dllPath to pstrPath
    const char* dllPath = "C:\\Users\\gsfchirmes\\Desktop\\camera"; 
    char* pstrPath= const_cast<char*>(dllPath);

    
    if (init==true) {
    //detecting camera, getting IP address
    cout<<fn_DetectCamera(pstrPath)<<endl;
    const char* cam_IP_const = fn_GetDetectedCameraIP(0);
    char* cam_IP = const_cast<char*>(cam_IP_const);
    int init_error = fn_Initialize(cam_IP,false,pstrPath);
    }
    fn_SetBrightness(-1000);
    fn_SetContrast(500);

    //getting image size and setting RAW Process option
    //int size_error = fn_GetImageSize(iWidth, iHeight); //<---Docs says needs ref, can take var as normal
    //int RAW_PROC_ERROR = fn_SetRAWProcessOption(1);



    //camera spamming loop
    for (int i = 0; i<numPics;i++) {
        std::byte* aImageDataDisplay;
        float* aImageDataRAW;
        aImageDataRAW = (float*)malloc(sizeof(float)*iImageSize);
        aImageDataDisplay = (std::byte*)malloc(sizeof(std::byte)*iImageSize);
        int camera_error = fn_GetCameraImage(aImageDataRAW,aImageDataDisplay,iImageSize);
        std::cout <<fn_ErrorToText(camera_error)<<std::endl;
        //adding data to compiled arrays here
        for (int j = 0; j < iImageSize; j++) {
            aImageDataRAW_comp[j] += aImageDataRAW[j];
        }
        //std::cout << aImageDataRAW[1000];
        //freeing arrays to be reinitialized
        free(aImageDataDisplay);
        free(aImageDataRAW);
    }
    //averaging frames over number of desired images
    for (int i = 0; i< iImageSize; i++){
        aImageDataRAW_comp[i] = aImageDataRAW_comp[i] / numPics;
    }

    // //prepping files for output
    ofstream outfile; 
    outfile.open(filename);
    int rows = 288;
    int cols = 384; //csv / image sizes

    //vectorizing RAW data array to write to file
    vector<vector<int>> ImageDataRAW(rows, vector<int>(cols));
    int index = 0;
    for(int i = 0;i<rows;i++) {
        for(int j = 0; j< cols; j++){
            ImageDataRAW[i][j] = aImageDataRAW_comp[index++];
        }
    }
    for(const auto &row : ImageDataRAW) {
        for (size_t i = 0; i < row.size(); ++i) {
            outfile << row[i];
            if (i != row.size() - 1) {
                outfile << ",";
            }
        }
        outfile << "\n";
    }
    outfile.close();
    free(aImageDataRAW_comp);
    free(aImageDataDisplay_comp);
    
    

return 0;

}

void frameAverages(int countOn, int countOff) {
    ofstream csvOn(csvPathOn);
    ofstream csvOff(csvPathOff);

    for (int y = 0; y<288;y++){
        for (int x=0; x<384; x++) {
            int idx = y*384 + x;
            double avgOn = accumOn[idx]/countOn;
            double avgOff = accumOff[idx]/countOff;
            csvOn<<avgOn;
            csvOff<<avgOff;
            if (x<383){
                csvOn << ",";
                csvOff << ",";
            }
        }
        csvOn << "\n";
        csvOff << "\n";
    }
    csvOn.close();
    csvOff.close();
    

}

int camera_trigger_function(uint16_t* pushRaw,
                            float* PfRawData,
                            unsigned char* pchDisplayData,
                            unsigned int iW,
                            unsigned int iH,
                            void* Pthis)
{   
    
    // Validate iW/iH just in case
    if (iW == 0 || iH == 0) return -1;
    {
        std::lock_guard<std::mutex> lock(mtx);
        
        // Copy incoming RAW frame using SDK-provided dims
        size_t pixels = static_cast<size_t>(iW) * static_cast<size_t>(iH);
        memcpy(&(*writeBuffer)[0][0], PfRawData, pixels * sizeof(float));
        //Swap buffers so proc thread sees new frame
        std::swap(writeBuffer, readBuffer);

        //Increment sequence BEFORE making frame available.
        frameSeq.fetch_add(1, std::memory_order_release);

        // Mark a new frame ready 
        newFrameAvailable.store(true, std::memory_order_release);
    }

    // Notify AFTER releasing lock
    cv.notify_one();
    return 0;
}

void processingLoop(int numFrames)
{
    if (numFrames <= 0) {
        std::cerr << "processingLoop: numFrames must be > 0\n";
        return;
    }

    int countOn = 0;
    int countOff = 0;
    int frameIndex = 0;
    static uint64_t lastSeq = 0;
    const int dbgPrintInterval = 101;
    int dbgIter = 0;
    while (true)
    {
        float* pixels = nullptr;
        uint64_t localSeq = 0;

        // --- LOCK + WAIT + CAPTURE  ---
        {
            std::unique_lock<std::mutex> lock(mtx);
            cv.wait(lock, [] { return newFrameAvailable.load(std::memory_order_acquire); });
            
            // capture the frame that triggered 
            pixels   = &(*readBuffer)[0][0];
            
            localSeq = frameSeq.load(std::memory_order_acquire);
            //this should be the most current image
            // mark frame as consumed
            newFrameAvailable.store(false, std::memory_order_release);
        } 

        // Frame-drop detection
        if (lastSeq != 0 && localSeq != lastSeq + 1) {
            std::cout << "FRAME DROPPED: expected " << (lastSeq + 1) << " but got " << localSeq << "\n";
        }
        lastSeq = localSeq;

        // Compute stats
        const size_t N = 384 * 288;
        uint64_t sum = 0;
        uint16_t minv = UINT16_MAX;
        uint16_t maxv = 0;
        double sq = 0.0;
        for (size_t i = 0; i < N; ++i) {
            uint16_t v = pixels[i];
            sum += v;
            if (v < minv) minv = v;
            if (v > maxv) maxv = v;
            sq += double(v) * double(v);
        }
        double mean = double(sum) / double(N);
        double variance = sq / double(N) - mean * mean;
        double stddev = sqrt(std::max(0.0, variance));

        // Decide ON/OFF from sequence localSeq parity
        bool laserOn = (localSeq % 2 == 1);

        // print stats periodically
        dbgIter++;
        if (dbgIter % dbgPrintInterval == 0) {
            std::cout << "SEQ=" << localSeq
                      << " frameIdx=" << frameIndex
                      << " laserOn=" << laserOn
                      << " sum=" << sum
                      << " mean=" << mean
                      << " std=" << stddev
                      << " min=" << minv
                      << " max=" << maxv
                      << " countOn=" << countOn
                      << " countOff=" << countOff
                      << "\n";

            std::cout << " first8: ";
            for (int i = 0; i < 8; ++i) std::cout << pixels[i] << " ";
            std::cout << "\n";
        }

        // Accumulate
        if (laserOn && countOn < numFrames)
        {
            for (size_t i = 0; i < N; ++i) accumOn[i] += pixels[i];
            ++countOn;
        }
        else if (!laserOn && countOff < numFrames)
        {
            for (size_t i = 0; i < N; ++i) accumOff[i] += pixels[i];
            ++countOff;
        }

        ++frameIndex;
        // Exit condition
        if (countOn >= numFrames && countOff >= numFrames)
        {
            std::cout << "Reached target frames: On=" << countOn << " Off=" << countOff << "\n";
            frameAverages(countOn, countOff);
            break;
        }
    }
}
void processingLoop_saveFrames(int numFrames)
{
    int countOn  = 0;
    int countOff = 0;

    while (true)
    {
        float* pixels = nullptr;
        uint64_t  localSeq = 0;

        // ================================
        // WAIT FOR NEW FRAME
        
        std::unique_lock<std::mutex> lock(mtx);
        cv.wait(lock, [] { return newFrameAvailable.load(std::memory_order_acquire); });

        // Capture pixels + sequence number while locked
        pixels = &(*readBuffer)[0][0];
        localSeq = frameSeq.load(std::memory_order_acquire);

        // Mark consumed
        newFrameAvailable.store(false, std::memory_order_release);

        // Release BEFORE processing
        lock.unlock();

        // Determine ON/OFF by sequence parity
        bool laserOn = (localSeq % 2 == 1);

        // =================================
        // SAVE FRAME TO CSV
        //OFFSET SUBTRACTION TEST-------------------------------------------------------------------------

        //------------------------------------------------------------------------------------------------
        unsigned short* aImageOffsetData;
        aImageOffsetData = (unsigned short*)malloc(sizeof(unsigned short)*384*288);
        int OFFSET_ERROR = fn_GetCameraImageOffset(aImageOffsetData, 288*384);
        
        for (int i=0;i<384*288;i++){
                if (i==0){
                    cout<<"Flag"<<endl;
                }
                pixels[i] = pixels[i] + aImageOffsetData[i];
            }
        cout<<aImageOffsetData[0]<<endl;
        free(aImageOffsetData);
        if (laserOn && countOn < numFrames)
        {
            // Construct filename
            std::ostringstream name;
            name << "MASS_IMAGE_BUFFER\\on_" << std::setw(4) << std::setfill('0') << countOn+1 << ".csv";
            std::ofstream f(name.str());

            // Write CSV
            for (int y = 0; y < 288; y++) {
                for (int x = 0; x < 384; x++) {
                    int idx = y*384 + x;
                    f << pixels[idx];
                    if (x < 383) f << ",";
                }
                f << "\n";
            }

            countOn++;
            std::cout << "Saved ON frame " << countOn << " (" << name.str() << ")\n";
        }
        else if (!laserOn && countOff < numFrames)
        {
            std::ostringstream name;
            name << "MASS_IMAGE_BUFFER\\off_" << std::setw(4) << std::setfill('0') << countOff+1 << ".csv";
            std::ofstream f(name.str());
        for (int y = 0; y < 288; y++) {
                for (int x = 0; x < 384; x++) {
                    int idx = y*384 + x;
                    f << pixels[idx];
                    if (x < 383) f << ",";
                }
                f << "\n";
            }

            countOff++;
            std::cout << "Saved OFF frame " << countOff << " (" << name.str() << ")\n";
        }

        // =================================
        // EXIT WHEN DONE
        // =================================
        if (countOn == numFrames && countOff == numFrames)
        {
            std::cout << "Finished saving " << numFrames
                      << " ON and " << numFrames << " OFF frames.\n";
            break;
        }
    }
}

DLLEXPORT int qcl_flash(char* onFile, char* offFile, int numFrames, int RAWPROC = 0) {

    cout<<"starting qcl flash..."<<endl;
    uint16_t (*pushRaw); //init pushRaw
    unsigned int iW = 384;
    unsigned int iH = 288; //image size
    int iImageSize = iH*iW;
    float* PfRawData = (float*)malloc(sizeof(float)*iImageSize);  //init pfraw
    unsigned char* pchDisplayData = (unsigned char*)malloc(sizeof(unsigned char)*iImageSize); //init display
    int iValSet = 1;
    int iValRet = 0;
    //------------------------------------------------------------------------------------process options
    int RAW_PROC_ERROR = fn_SetRAWProcessOption(0); //SETTING RAW PROC OPTION 0-none 1-offset correction
    int dummy;
    fn_SetShutterPosition(0,dummy);
    int retGain;
    fn_SetGain(7,retGain);
    //-------------------------------------------------------------------------------------
    csvPathOn = onFile;
    csvPathOff = offFile;
    size_t N = 384 * 288;
    accumOn.assign(N, 0.0);
    accumOff.assign(N, 0.0);
    frameSeq.store(0, std::memory_order_release);
    //CALLBACK SETUP-----------------------------------------------------------------------
    int (*pCallback) (uint16_t*,float*,unsigned char*,unsigned int,unsigned int,void*);
    pCallback = camera_trigger_function;
    void (*pThis) = nullptr;

    int trigger_error = fn_SetExternalTrigger(iValSet, iValRet);
    cout<<"iValRet: "<<iValRet<<endl;
    cout<<"trigger error: "<<fn_ErrorToText(trigger_error)<<endl;

    
    
    //INO SUGGESTS OFFSET AFTER ENABLING TRIGGER
    // int iNbrFrame = 16;
    // bool bUseInternalShutter = true;
    // bool bVerbose = false;

    
    // //-------------------
    
    //callback------------------------------------------------------------
    int callback_error = fn_SetCameraCallback(pCallback, pThis);
    cout<<"callback_error: "<<fn_ErrorToText(callback_error)<<endl;

    int OFFSET_ERROR = fn_TakeOffset(16,false, false);
    cout<<"OFFSET ERROR: "<<fn_ErrorToText(OFFSET_ERROR)<<endl;
    std::this_thread::sleep_for(std::chrono::seconds(3));

    int RAW_PROC_ERROR2 = fn_SetRAWProcessOption(0); //SETTING RAW PROC OPTION 0-none 1-offset correction
    processingLoop(numFrames);
    //------------------------------------------------------
    
    fn_SetExternalTrigger(0,iValRet);
    frameSeq.store(0,std::memory_order_release);
    cout<<"complete"<<endl;
    return 0;
}

void saveFrame(const char* filename, Frame* frame){
    ofstream file(filename);
    float* pixels = &(*frame)[0][0];

    for (int y = 0; y<288;y++){
        for (int x = 0; x< 384; x++){
            file << pixels[y*384 + x];
            if (x<383){
                file<<",";
            }file<<"\n";

        }file.close();
    }



}

DLLEXPORT void run_time_constant_test(const char* outDir, int seconds) {
    filesystem::create_directories(outDir);
    int frameLimit = seconds*50;
    int captured = 0;

    auto start = chrono::steady_clock::now();

    while (captured<frameLimit) {
        unique_lock<mutex> lock(mtx);
        cv.wait(lock, [] {return newFrameAvailable.load(memory_order_acquire); });

        newFrameAvailable.store(false, memory_order_release);
        lock.unlock();

        auto now = chrono::steady_clock::now();
        auto elapsed_ns = chrono::duration_cast<chrono::nanoseconds>(now-start).count();

        string filename = string(outDir) + "\\image_" + to_string(elapsed_ns)+".csv";
        saveFrame(filename.c_str(), readBuffer);
        captured++;
    

    }
}









