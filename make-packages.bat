set destination=C:\inetpub\wwwroot\eWamUpdate

cd /d %~dp0

python packagebuilder.py D:\wyde\ --package-index-policy overwrite --deploy %destination% --wipe-destination

REM python packagebuilder.py D:\wyde\eWAM --package-index-policy overwrite --deploy %destination% --wipe-destination
REM python packagebuilder.py D:\wyde\Wynsure --package-index-policy append --deploy %destination%

pause