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

#define GRAB_FRAME_FOREVER	0x8888

typedef struct {
    int CameraID;
    int ExposureTime;
    int TimeStamp;
    int TriggerOccurred;
    int TriggerEventCount;
    int OverSaturated;
    int LightShieldAverageValue;
} TProcessedDataProperty;


typedef void (* DeviceFaultCallBack)( int DeviceType );
typedef void (* FrameDataCallBack)(int FrameType, int Row, int Col, 
				  TProcessedDataProperty* Attributes, unsigned char *BytePtr );

// Export functions:
SDK_API CCDUSB_InitDevice( void );
SDK_API CCDUSB_UnInitDevice( void );
SDK_API CCDUSB_GetModuleNoSerialNo( int DeviceID, char *ModuleNo, char *SerialNo);
SDK_API CCDUSB_AddDeviceToWorkingSet( int DeviceID );
SDK_API CCDUSB_RemoveDeviceFromWorkingSet( int DeviceID );
SDK_API CCDUSB_StartCameraEngine( HWND ParentHandle );
SDK_API CCDUSB_StopCameraEngine( void );
SDK_API CCDUSB_SetBitMode( int DeviceID, int BitMode );
SDK_API CCDUSB_SetCameraWorkMode( int DeviceID, int WorkMode );
SDK_API CCDUSB_StartFrameGrab( int TotalFrames );
SDK_API CCDUSB_StopFrameGrab( void );
SDK_API CCDUSB_ShowFactoryControlPanel( int DeviceID, char *passWord );
SDK_API CCDUSB_HideFactoryControlPanel( void );
SDK_API CCDUSB_SetExposureTime( int DeviceID, int exposureTime, bool Store );
SDK_API CCDUSB_SetGains( int DeviceID, int RGain, int GGain, int BGain );
SDK_API CCDUSB_SetFrameTime( int DeviceID, int FrameTime );
SDK_API CCDUSB_InstallFrameHooker( int FrameType, FrameDataCallBack FrameHooker );
SDK_API CCDUSB_InstallUSBDeviceHooker( DeviceFaultCallBack USBDeviceHooker );
SDK_API CCDUSB_SetSoftTrigger( int DeviceID );
SDK_API CCDUSB_SetTriggerBurstCount (int DeviceID, int BurstCount );
SDK_API CCDUSB_SetTriggerBurstFrameTime (int DeviceID, int BurstFrameTime );
SDK_POINTER_API CCDUSB_GetCurrentFrame( int DeviceID, unsigned short* &FramePtr );
SDK_API CCDUSB_SetOBDarkCompensation( int CompensationOn );
SDK_API CCDUSB_SetGPIOConifg( int DeviceID, unsigned char ConfigByte );
SDK_API CCDUSB_SetGPIOInOut( int DeviceID, unsigned char OutputByte,
                             unsigned char *InputBytePtr );


