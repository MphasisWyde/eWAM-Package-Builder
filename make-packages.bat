set destination=C:\inetpub\wwwroot\eWamUpdate

cd /d %~dp0

python packagebuilder.py D:\wyde\ C:\inetpub\wwwroot --package-index-policy update-keep-old-packages --deploy %destination% --deploy-policy update

pause