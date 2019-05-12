@echo off
set prog=%~n0
set fullprog=%~n0%~x0
setlocal enableDelayedExpansion
set "options=-min:0 -max:10"

title Starting %prog% %*: %date% %time%
echo Starting %fullprog% %*: %date% %time%

REM from https://stackoverflow.com/questions/3973824/windows-bat-file-optional-argument-parsing
@echo off
for %%O in (%options%) do for /f "tokens=1,* delims=:" %%A in ("%%O") do set "%%A=%%~B"

:loop
if not "%~1"=="" (
  set "test=!options:*%~1:=! "
  if "!test!"=="!options! " (
      rem echo Error: Invalid option %~1
  ) else if "!test:~0,1!"==" " (
      set "%~1=1"
  ) else (
      setlocal disableDelayedExpansion
      set "val=%~2"
      call :escapeVal
      setlocal enableDelayedExpansion
      for /f delims^=^ eol^= %%A in ("!val!") do endlocal&endlocal&set "%~1=%%A" !
      shift /1
  )
  shift /1
  goto :loop
)
goto :endArgs

:escapeVal
set "val=%val:^=^^%"
set "val=%val:!=^!%"
exit /b

:endArgs
:: set -
:: To get the value of a single parameter, just remember to include the `-`

title Running %prog% %*: %date% %time%
echo Running %fullprog% %*: %date% %time%
echo Min: %-min% Max: %-max% for %prog% %*
rem SET /A rand=!RANDOM! * 10 / 32768 + 1
rem shuf -i 1-10 -n 1
for /f "tokens=*" %%i in ('cmd /c shuf -i %-min%-%-max% -n 1') do set rand=%%i
rem cmd /c cmd
echo Sleeping %rand%s for %prog% %*
sleep %rand%
title Done running %prog% %*: %date% %time%
echo Done running %fullprog% %*: %date% %time%
