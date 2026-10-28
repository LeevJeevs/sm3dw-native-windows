@echo off
call "%~dp0env.bat"
set ROOT=%~dp0..
cmake -S "%ROOT%\tools\analyzer-only" -B "%ROOT%\build\analyzer" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_TOOLCHAIN_FILE="%ROOT%\third_party\vcpkg\scripts\buildsystems\vcpkg.cmake" || exit /b 1
cmake --build "%ROOT%\build\analyzer" || exit /b 1
