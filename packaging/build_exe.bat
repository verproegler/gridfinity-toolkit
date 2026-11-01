@echo off
rem Builds "dist\Gridfinity Toolkit\Gridfinity Toolkit.exe" with PyInstaller.
cd /d "%~dp0\.."
python -m pip install --upgrade pyinstaller -r requirements.txt || goto :error
python -m PyInstaller --noconfirm --clean --windowed ^
  --name "Gridfinity Toolkit" ^
  --paths "%CD%" ^
  --add-data "%CD%\assets;assets" ^
  --add-data "%CD%\LICENSE;." ^
  --add-data "%CD%\THIRD_PARTY_LICENSES.md;." ^
  --collect-all manifold3d ^
  --collect-submodules OpenGL ^
  --collect-submodules pyopengltk ^
  --distpath dist --workpath build --specpath build ^
  packaging\run_toolkit.py || goto :error
echo.
echo Done: dist\Gridfinity Toolkit\Gridfinity Toolkit.exe
exit /b 0
:error
echo Build failed.
exit /b 1
