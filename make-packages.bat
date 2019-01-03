set destination=C:\inetpub\wwwroot\eWamUpdate

cd /d %~dp0

python packagebuilder.py D:\wyde\ C:\inetpub\wwwroot --package-index-policy update --deploy %destination% --deploy-policy update

pause