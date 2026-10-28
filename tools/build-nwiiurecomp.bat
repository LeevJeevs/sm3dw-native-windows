@echo off
rem Builds third_party\nWiiURecomp with MSVC.
rem   BUILD_DIR        output dir (default build\nwiiurecomp)
rem   EXTRA_CMAKE_ARGS extra cmake args, e.g. -DCMAKE_CXX_FLAGS=/DNWIIU_MEM2_HEAP_BASE=0x10E40000u
call "%~dp0env.bat"
set ROOT=%~dp0..
if "%BUILD_DIR%"=="" set BUILD_DIR=%ROOT%\build\nwiiurecomp
if "%BUILD_TARGET%"=="" set BUILD_TARGET=all
set VCPKG_ROOT=%ROOT%\third_party\vcpkg
set PKG_CONFIG=%VCPKG_ROOT%\installed\x64-windows-release\tools\pkgconf\pkgconf.exe
set PKG_CONFIG_PATH=%VCPKG_ROOT%\installed\x64-windows-release\lib\pkgconfig
cmake -S "%ROOT%\third_party\nWiiURecomp" -B "%BUILD_DIR%" -G Ninja -DCMAKE_BUILD_TYPE=Release ^
  -DCMAKE_TOOLCHAIN_FILE="%VCPKG_ROOT%\scripts\buildsystems\vcpkg.cmake" ^
  -DVCPKG_TARGET_TRIPLET=x64-windows-release -DVCPKG_OVERLAY_TRIPLETS="%ROOT%\tools\vcpkg-triplets" ^
  -DPKG_CONFIG_EXECUTABLE="%PKG_CONFIG%" %EXTRA_CMAKE_ARGS% || exit /b 1
cmake --build "%BUILD_DIR%" --target %BUILD_TARGET% -- -k 0 || exit /b 1
