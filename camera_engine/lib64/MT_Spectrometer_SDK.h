// The following ifdef block is the standard way of creating macros which make exporting 
// from a DLL simpler. All files within this DLL are compiled with the MTUSBDLL_EXPORTS
// symbol defined on the command line. this symbol should not be defined on any project
// that uses this DLL. This way any other project whose source files include this file see 
// MTUSBDLL_API functions as being imported from a DLL, wheras this DLL sees symbols
// defined with this macro as being exported.
typedef int SDK_RETURN_CODE;
typedef unsigned int DEV_HANDLE;

#ifdef SDK_EXPORTS
#define SDK_API extern "C" __declspec(dllexport) SDK_RETURN_CODE _cdecl
#define SDK_HANDLE_API extern "C" __declspec(dllexport) DEV_HANDLE _cdecl
#define SDK_POINTER_API extern "C" __declspec(dllexport) unsigned short * _cdecl
#else
#define SDK_API extern "C" __declspec(dllimport) SDK_RETURN_CODE _cdecl
#define SDK_HANDLE_API extern "C" __declspec(dllimport) DEV_HANDLE _cdecl
#define SDK_POINTER_API extern "C" __declspec(dllimport) unsigned short * _cdecl
#endif

typedef struct
{
  double* RawData;
  double* CalibData;
  double* AbsInten;
}tFrameRecord;

typedef struct 
{
  int CameraID;
  int ExposureTime;
  int TimeStamp;
  int TriggerOccurred;
  int TriggerEventCount;
  int OverSaturated;
  int LightShieldValue;
} TFrameDataProperty;

typedef void (* DeviceFrameDataCallBack)(int Row, int Col, 
                                         TFrameDataProperty* Attributes, void **FramePtr );

SDK_API MTSSE_InitDevice(HWND ParentHandle );
SDK_API MTSSE_UnInitDevice( void );
SDK_API MTSSE_GetDeviceModuleNoSerialNo( int DeviceID, char* ModuleNo, char* SerialNo );
SDK_API MTSSE_GetDeviceSpectrometerWavCalPara( int DeviceID, int SpectrometerID, double* &WavCalibValue);
SDK_API MTSSE_SetDeviceActiveStatus( int DeviceID, int ActiveFlag );
SDK_API MTSSE_InstallDeviceFrameHooker(int DeviceNo, DeviceFrameDataCallBack DeviceHookerProc);
SDK_API MTSSE_SetDeviceAverageFrameNum( int DeviceID, int AverageFrameCount );
SDK_API MTSSE_SetDeviceWorkMode( int DeviceID, int WorkMode );
SDK_API MTSSE_SetDeviceSoftTrigger(int DeviceID);
SDK_API MTSSE_SetDeviceExposureTime( int DeviceID, int ExposureTime );
SDK_API MTSSE_StartFrameGrab( int GrabType );
SDK_API MTSSE_StopFrameGrab( void );
SDK_API MTSSE_SetDeviceSpectrometerAutoDarkStatus( int DeviceID, int SpectrometerID, int AutoDrkFlag );
SDK_API MTSSE_SetDeviceSpectrometerETCStatus( int DeviceID, int SpectrometerID, int ETCFlag );
SDK_API MTSSE_SetDeviceSpectrometerDarkData( int DeviceID, int SpectrometerID, double *DarkData );
SDK_API MTSSE_GetDeviceSpectrometerFrameData(int DeviceID, int SpectrometerID, int WaitUntilDone, tFrameRecord* &FrameData );
SDK_API MTSSE_GetDeviceSpectrometerFrameDataProperty( int DeviceID,int SpectrometerID,int WaitUntilDone,TFrameDataProperty* FrameProperty,tFrameRecord* &FrameData);
SDK_API MTSSE_SaveDeviceSpectrometerWavCalPara( int DeviceID, int SpectrometerID, double* WavCalibArray);//
SDK_API MTSSE_GetDeviceSpectrometerCIE1931Coords( int DeviceID, int SpectrometerID, double* FrameData, double &x, double &y );
SDK_API MTSSE_GetDeviceSpectrometerCIE1976Coords( int DeviceID, int SpectrometerID, double* FrameData, double &u, double &v );  
SDK_API MTSSE_GetDeviceSpectrometerCCT( int DeviceID, int SpectrometerID, double* FrameData, int &CCT);
SDK_API MTSSE_GetDeviceSpectrometerCRIs( int DeviceID, int SpectrometerID, double* FrameData, double *CRIs);
SDK_API MTSSE_SetDeviceGPIOConfig( int DeviceID, int Config );
SDK_API MTSSE_SetDeviceGPIOInOut( int DeviceID, int Output, unsigned char *Input );
